"""main.py 的桌面 GUI：输入 API Key 和任务提示，启动/停止 Manus agent，并实时显示日志。"""

import asyncio
import os
import queue
import threading
import tkinter as tk
from tkinter import scrolledtext


class ManusGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("OpenManus - Manus Agent")
        self.root.geometry("860x780")

        self.log_queue: queue.Queue = queue.Queue()
        self.result_queue: queue.Queue = queue.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task | None = None
        self._log_handler_id: int | None = None
        self._worker_thread: threading.Thread | None = None

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

        # 开始 / 停止按钮
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

        # 日志输出区域（支持滚动）
        log_frame = tk.Frame(self.root)
        log_frame.pack(fill=tk.BOTH, expand=True, **pad)
        tk.Label(log_frame, text="执行日志:").pack(anchor=tk.W)
        self.log_area = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, state=tk.DISABLED, height=12
        )
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # 执行结果输出区域
        result_frame = tk.Frame(self.root)
        result_frame.pack(fill=tk.BOTH, expand=True, **pad)
        tk.Label(result_frame, text="执行结果:").pack(anchor=tk.W)
        self.result_area = scrolledtext.ScrolledText(
            result_frame, wrap=tk.WORD, state=tk.DISABLED, height=10
        )
        self.result_area.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

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
        self.log_queue.put(str(message))

    # ---------- 执行结果 ----------

    def _set_result(self, text: str):
        self.result_area.configure(state=tk.NORMAL)
        self.result_area.delete("1.0", tk.END)
        self.result_area.insert(tk.END, text)
        self.result_area.see(tk.END)
        self.result_area.configure(state=tk.DISABLED)

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
        if api_key:
            # 必须在 app.config 加载前设置，配置加载时会读取该环境变量
            os.environ["DASHSCOPE_API_KEY"] = api_key

        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self._set_result("")  # 开始新任务前清空上次结果
        self._append_log(f"[任务] 开始执行: {prompt}\n")

        self._worker_thread = threading.Thread(
            target=self._run_agent, args=(prompt, api_key), daemon=True
        )
        self._worker_thread.start()

    def stop_task(self):
        if self._loop and self._task and not self._task.done():
            self._loop.call_soon_threadsafe(self._task.cancel)
            self._append_log("[任务] 正在停止...\n")
        self.stop_btn.configure(state=tk.DISABLED)

    def _run_agent(self, prompt: str, api_key: str):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._agent_coro(prompt, api_key))
        finally:
            self._loop.close()
            self._loop = None
            self._task = None
            self.root.after(0, self._reset_buttons)

    async def _agent_coro(self, prompt: str, api_key: str):
        from app.agent.manus import Manus
        from app.config import config
        from app.logger import logger

        # 输入框中的 key 优先于 config.toml 中的 api_key
        if api_key:
            config.llm["default"].api_key = api_key
            if "vision" in config.llm:
                config.llm["vision"].api_key = api_key

        # 将 logger 输出同时转发到 GUI 日志区域
        self._log_handler_id = logger.add(self._enqueue_log)

        agent = await Manus.create()
        try:
            self._task = asyncio.ensure_future(agent.run(prompt))
            result = await self._task
            self.log_queue.put("[任务] 请求处理完成。\n")
            # 将 agent.run 返回值写入结果区域
            self.result_queue.put(result if result else "(无返回结果)")
        except asyncio.CancelledError:
            self.log_queue.put("[任务] 已被用户停止。\n")
            self.result_queue.put("[任务已停止]")
        except Exception as e:
            self.log_queue.put(f"[错误] {e}\n")
            self.result_queue.put(f"[错误] {e}")
        finally:
            if self._log_handler_id is not None:
                logger.remove(self._log_handler_id)
                self._log_handler_id = None
            await agent.cleanup()

    def _reset_buttons(self):
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)

    def _on_close(self):
        self.stop_task()
        self.root.destroy()


def run_gui():
    root = tk.Tk()
    ManusGUI(root)
    root.mainloop()
