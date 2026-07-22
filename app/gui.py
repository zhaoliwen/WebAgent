"""main.py 的桌面 GUI：输入 API Key 和任务提示，启动/停止 Manus agent，并实时显示日志。"""

import asyncio
import html
import os
import queue
import sys
import threading
import traceback
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import scrolledtext

import markdown
from tkinterweb import HtmlFrame


class ManusGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("livan")
        self.root.geometry("860x780")

        self.log_queue: queue.Queue = queue.Queue()
        self.result_queue: queue.Queue = queue.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task | None = None
        self._log_handler_id: int | None = None
        self._worker_thread: threading.Thread | None = None
        # 用户点击停止时置 True，打断当前轮并阻止开启下一轮
        self._stop_requested = False

        self._build_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._poll_log_queue)
        self.root.after(100, self._poll_result_queue)

    def _build_widgets(self):
        pad = {"padx": 10, "pady": 5}

        # API Key 输入框
        key_frame = tk.Frame(self.root)
        key_frame.pack(fill=tk.X, **pad)
        tk.Label(key_frame, text="API Key:").pack(side=tk.LEFT)
        self.key_entry = tk.Entry(key_frame, show="*")
        self.key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        # 已设置环境变量时预填，方便确认
        env_key = os.getenv("DASHSCOPE_API_KEY", "")
        if env_key:
            self.key_entry.insert(0, env_key)

        # 任务提示多行输入框
        prompt_frame = tk.Frame(self.root)
        prompt_frame.pack(fill=tk.X, **pad)
        tk.Label(prompt_frame, text="请输入你的具体要求:").pack(anchor=tk.W)
        self.prompt_text = tk.Text(prompt_frame, height=5, wrap=tk.WORD)
        self.prompt_text.pack(fill=tk.X, pady=(5, 0))

        # 开始 / 停止按钮 + 循环执行
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, **pad)
        self.start_btn = tk.Button(
            btn_frame, text="开始执行", width=12, command=self.start_task
        )
        self.start_btn.pack(side=tk.LEFT)
        self.stop_btn = tk.Button(
            btn_frame,
            text="停止执行",
            width=12,
            command=self.stop_task,
            state=tk.DISABLED,
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(10, 0))
        # 勾选后：本轮结束后用相同提示词自动开启下一轮；运行中取消勾选则本轮结束后停止
        self.loop_var = tk.BooleanVar(value=False)
        self.loop_check = tk.Checkbutton(
            btn_frame,
            text="循环执行",
            variable=self.loop_var,
        )
        self.loop_check.pack(side=tk.LEFT, padx=(16, 0))

        # 日志输出区域（支持滚动）
        log_frame = tk.Frame(self.root)
        log_frame.pack(fill=tk.BOTH, expand=True, **pad)
        tk.Label(log_frame, text="执行日志:").pack(anchor=tk.W)
        self.log_area = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, state=tk.DISABLED, height=12
        )
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # 执行结果：Markdown 转 HTML 后由内嵌浏览器控件渲染
        result_frame = tk.Frame(self.root)
        result_frame.pack(fill=tk.BOTH, expand=True, **pad)
        tk.Label(result_frame, text="执行结果:").pack(anchor=tk.W)
        self.result_view = HtmlFrame(
            result_frame, messages_enabled=False, vertical_scrollbar=True
        )
        self.result_view.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        self._set_result("")

    # ---------- 日志 ----------

    def _append_log(self, message: str):
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.insert(tk.END, message)
        self.log_area.see(tk.END)  # 自动滚动到底部
        self.log_area.configure(state=tk.DISABLED)

    def _poll_log_queue(self):
        try:
            while True:
                self._append_log(self.log_queue.get_nowait())
        except queue.Empty:
            pass
        self.root.after(100, self._poll_log_queue)

    def _enqueue_log(self, message):
        # loguru sink：在 agent 所在线程被调用，仅做入队，由 UI 线程消费
        text = str(message)
        if not text.endswith("\n"):
            text += "\n"
        self.log_queue.put(text)

    def _ui_log(self, message: str):
        """不依赖 loguru，直接把进度写到界面。"""
        if not message.endswith("\n"):
            message += "\n"
        self.log_queue.put(message)

    def _write_crash_log(self, text: str):
        """将错误写入 exe 旁 logs/gui_error.log，方便打包后排查。"""
        try:
            from app.config import PROJECT_ROOT

            log_dir = Path(PROJECT_ROOT) / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            crash_path = log_dir / "gui_error.log"
            with crash_path.open("a", encoding="utf-8") as f:
                f.write(f"\n===== {datetime.now().isoformat()} =====\n")
                f.write(text)
                if not text.endswith("\n"):
                    f.write("\n")
            self._ui_log(f"[提示] 详细错误已写入: {crash_path}")
        except Exception as e:
            self._ui_log(f"[提示] 写入错误日志失败: {e}")

    # ---------- 执行结果（Markdown -> HTML） ----------

    def _wrap_result_html(self, body: str) -> str:
        """包裹为完整 HTML 页面，便于内嵌浏览器渲染。"""
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  body {{
    margin: 0;
    padding: 12px 14px;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 14px;
    line-height: 1.65;
    color: #1f2937;
    background: #ffffff;
  }}
  h1, h2, h3, h4 {{
    margin: 1.1em 0 0.45em;
    line-height: 1.3;
    color: #111827;
  }}
  h1 {{ font-size: 1.45em; }}
  h2 {{ font-size: 1.28em; }}
  h3 {{ font-size: 1.12em; }}
  p {{ margin: 0.55em 0; }}
  ul, ol {{ margin: 0.45em 0 0.45em 1.3em; padding: 0; }}
  li {{ margin: 0.2em 0; }}
  a {{ color: #2563eb; }}
  code {{
    font-family: Consolas, "Courier New", monospace;
    font-size: 0.92em;
    background: #f3f4f6;
    padding: 0.1em 0.35em;
    border-radius: 3px;
  }}
  pre {{
    background: #f3f4f6;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 10px 12px;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-word;
  }}
  pre code {{
    background: transparent;
    padding: 0;
  }}
  blockquote {{
    margin: 0.6em 0;
    padding: 0.2em 0.8em;
    border-left: 4px solid #d1d5db;
    color: #4b5563;
    background: #f9fafb;
  }}
  table {{
    border-collapse: collapse;
    margin: 0.7em 0;
    width: 100%;
  }}
  th, td {{
    border: 1px solid #d1d5db;
    padding: 6px 10px;
    text-align: left;
  }}
  th {{ background: #f3f4f6; }}
  hr {{
    border: none;
    border-top: 1px solid #e5e7eb;
    margin: 1em 0;
  }}
</style>
</head>
<body>
{body}
</body>
</html>"""

    def _markdown_to_html_body(self, text: str) -> str:
        """将结果文本转为 HTML 正文。错误堆栈用纯文本，避免被当成标签。"""
        stripped = text.strip()
        if not stripped:
            return "<p></p>"

        # 停止提示、Python 堆栈等按纯文本展示
        if stripped.startswith("[任务已停止]") or stripped.startswith(
            "Traceback"
        ) or "\nTraceback (most recent call last):" in text[:800]:
            return f"<pre>{html.escape(text)}</pre>"

        return markdown.markdown(
            text,
            extensions=["fenced_code", "tables", "nl2br", "sane_lists"],
            output_format="html",
        )

    def _set_result(self, text: str):
        body = self._markdown_to_html_body(text or "")
        self.result_view.load_html(self._wrap_result_html(body))

    def _poll_result_queue(self):
        try:
            while True:
                self._set_result(self.result_queue.get_nowait())
        except queue.Empty:
            pass
        self.root.after(100, self._poll_result_queue)

    # ---------- 任务控制 ----------

    def start_task(self):
        prompt = self.prompt_text.get("1.0", tk.END).strip()
        if not prompt:
            self._append_log("[提示] 请先输入具体要求。\n")
            return

        api_key = self.key_entry.get().strip()
        if not api_key:
            self._append_log("[提示] 请先填写 API Key。\n")
            return

        # 必须在创建 LLM 客户端前设置
        os.environ["DASHSCOPE_API_KEY"] = api_key

        self._stop_requested = False
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self._set_result("")  # 开始新任务前清空上次结果
        loop_hint = "（已开启循环执行）" if self.loop_var.get() else ""
        self._append_log(f"[任务] 开始执行{loop_hint}: {prompt}\n")

        self._worker_thread = threading.Thread(
            target=self._run_agent, args=(prompt, api_key), daemon=True
        )
        self._worker_thread.start()

    def stop_task(self):
        self._stop_requested = True
        if self._loop and self._task and not self._task.done():
            self._loop.call_soon_threadsafe(self._task.cancel)
            self._append_log("[任务] 正在停止...\n")
        elif self._worker_thread and self._worker_thread.is_alive():
            self._append_log("[任务] 已请求停止，将在本轮结束后退出循环。\n")
        self.stop_btn.configure(state=tk.DISABLED)

    def _run_agent(self, prompt: str, api_key: str):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._agent_coro(prompt, api_key))
        except Exception:
            tb = traceback.format_exc()
            self._ui_log(f"[致命错误]\n{tb}")
            self.result_queue.put(tb)
            self._write_crash_log(tb)
        finally:
            try:
                self._loop.close()
            except Exception:
                pass
            self._loop = None
            self._task = None
            self.root.after(0, self._reset_buttons)

    async def _agent_coro(self, prompt: str, api_key: str):
        """执行任务；若勾选循环执行，则每轮结束后用相同提示词开启新一轮。"""
        try:
            self._ui_log("[进度] 正在加载模块...")
            from app.agent.manus import Manus
            from app.config import PROJECT_ROOT, config
            from app.llm import LLM
            from app.logger import logger

            self._ui_log(f"[进度] 项目目录: {PROJECT_ROOT}")

            # 输入框中的 key 优先；并清掉旧 LLM 单例，避免沿用空 key 创建的客户端
            config.llm["default"].api_key = api_key
            if "vision" in config.llm:
                config.llm["vision"].api_key = api_key
            LLM._instances.clear()
            self._ui_log(
                f"[进度] 已注入 API Key（长度 {len(api_key)}），"
                f"模型={config.llm['default'].model}"
            )

            # 将 logger 输出同时转发到 GUI 日志区域
            self._log_handler_id = logger.add(
                self._enqueue_log,
                level="DEBUG",
                format="{time:HH:mm:ss} | {level:<8} | {message}",
                enqueue=True,
            )

            round_idx = 0
            while not self._stop_requested:
                round_idx += 1
                agent = None
                try:
                    if round_idx > 1:
                        self._ui_log(f"[任务] 循环执行：开始第 {round_idx} 轮...")
                    else:
                        self._ui_log("[进度] 正在创建 Manus agent...")

                    agent = await Manus.create()
                    self._ui_log(
                        f"[进度] Agent 已创建，开始执行任务"
                        f"（第 {round_idx} 轮）..."
                    )

                    self._task = asyncio.ensure_future(agent.run(prompt))
                    result = await self._task
                    self._ui_log(f"[任务] 第 {round_idx} 轮处理完成。")
                    self.result_queue.put(result if result else "(无返回结果)")
                except asyncio.CancelledError:
                    self._ui_log("[任务] 已被用户停止。")
                    self.result_queue.put("[任务已停止]")
                    self._stop_requested = True
                    break
                except Exception:
                    tb = traceback.format_exc()
                    self._ui_log(f"[错误]\n{tb}")
                    self.result_queue.put(tb)
                    self._write_crash_log(tb)
                    # 出错不再自动开下一轮，避免错误循环刷屏
                    break
                finally:
                    if agent is not None:
                        try:
                            await agent.cleanup()
                        except Exception as e:
                            self._ui_log(f"[提示] cleanup 异常: {e}")
                    self._task = None

                if self._stop_requested:
                    break
                # 每轮结束后再读复选框：运行中取消勾选则本轮结束后停止
                if not self.loop_var.get():
                    break
                self._ui_log("[任务] 循环执行：即将用相同提示词开启下一轮...")
        finally:
            if self._log_handler_id is not None:
                try:
                    from app.logger import logger

                    logger.remove(self._log_handler_id)
                except Exception:
                    pass
                self._log_handler_id = None

    def _reset_buttons(self):
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)

    def _on_close(self):
        self.stop_task()
        self.root.destroy()


def run_gui():
    # 启动诊断：同时写 TEMP 与 exe 旁，避免路径识别错误时完全看不到日志
    boot_lines = [
        f"frozen={getattr(sys, 'frozen', None)}",
        f"meipass={getattr(sys, '_MEIPASS', None)}",
        f"exe={sys.executable}",
        f"cwd={os.getcwd()}",
        f"argv={sys.argv!r}",
    ]
    try:
        from app.config import PROJECT_ROOT

        boot_lines.append(f"PROJECT_ROOT={PROJECT_ROOT}")
        boot_lines.append(
            f"config_exists={(PROJECT_ROOT / 'config' / 'config.toml').exists()}"
        )
    except Exception as e:
        boot_lines.append(f"config_import_error={e!r}")

    boot_text = "\n".join(boot_lines) + "\n"
    for target in (
        Path(os.environ.get("TEMP", ".")) / "openmanus_boot.log",
        Path(sys.executable).resolve().parent / "logs" / "gui_boot.log",
    ):
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(boot_text, encoding="utf-8")
        except Exception:
            pass

    root = tk.Tk()
    ManusGUI(root)
    root.mainloop()
