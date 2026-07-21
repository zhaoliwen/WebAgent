import argparse
import asyncio

from app.logger import logger


async def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="运行 Manus agent")
    parser.add_argument(
        "--prompt", type=str, required=False, help="帮我再百度搜索一下：今日A股上证指数的收盘价是多少？"
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
    import sys

    if "--prompt" in sys.argv:
        # 命令行模式：直接执行，不启动 GUI
        asyncio.run(main())
    else:
        # 默认启动图形界面
        from app.gui import run_gui

        run_gui()
