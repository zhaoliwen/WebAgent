import argparse
import asyncio
import multiprocessing
import os
import sys
from pathlib import Path


def _bootstrap_frozen() -> None:
    """打包为 exe 后的启动修复（与 python main.py 的关键差异）。

    1. 工作目录切到 exe 所在目录，保证旁路 config/、workspace/ 可读
    2. windowed 模式下 stdout/stderr 为 None，会导致日志/部分库异常被吞掉
    """
    exe_dir = Path(sys.executable).resolve().parent
    is_frozen = (
        getattr(sys, "frozen", False)
        or hasattr(sys, "_MEIPASS")
        or ((exe_dir / "_internal").is_dir() and (exe_dir / "OpenManus.exe").is_file())
    )
    if not is_frozen:
        return

    os.chdir(exe_dir)

    log_dir = exe_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    runtime_log = open(log_dir / "runtime.log", "a", encoding="utf-8", buffering=1)
    runtime_log.write(
        f"\n===== boot =====\n"
        f"frozen={getattr(sys, 'frozen', None)} "
        f"meipass={getattr(sys, '_MEIPASS', None)} "
        f"exe={sys.executable}\n"
    )
    runtime_log.flush()
    if sys.stdout is None:
        sys.stdout = runtime_log
    if sys.stderr is None:
        sys.stderr = runtime_log


async def main():
    from app.logger import logger

    # 解析命令行参数
    parser = argparse.ArgumentParser(description="运行 Manus agent")
    parser.add_argument(
        "--prompt",
        type=str,
        required=False,
        help="帮我再百度搜索一下：今日A股上证指数的收盘价是多少？",
    )
    args = parser.parse_args()

    from app.agent.manus import Manus

    # 创建并初始化 Manus agent
    agent = await Manus.create()
    try:
        # 如果提供了命令行提示，则使用它；否则询问用户输入
        prompt = args.prompt if args.prompt else input("请输入你的提示: ")
        if not prompt.strip():
            logger.warning("提供的提示为空。")
            return

        logger.warning("正在处理你的请求...")
        await agent.run(prompt)
        logger.info("请求处理完成。")
    except KeyboardInterrupt:
        logger.warning("操作被中断。")
    finally:
        # 确保在退出前清理 agent 资源
        await agent.cleanup()


if __name__ == "__main__":
    # Windows 打包后子进程/部分依赖需要
    multiprocessing.freeze_support()
    _bootstrap_frozen()

    if "--prompt" in sys.argv:
        # 命令行模式：直接执行，不启动 GUI
        asyncio.run(main())
    else:
        # 默认启动图形界面
        from app.gui import run_gui

        run_gui()
