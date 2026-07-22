import sys
from datetime import datetime

from loguru import logger as _logger

from app.config import PROJECT_ROOT


_print_level = "INFO"


def define_log_level(print_level="INFO", logfile_level="DEBUG", name: str = None):
    """将日志级别调整到指定级别"""
    global _print_level
    _print_level = print_level

    current_date = datetime.now()
    formatted_date = current_date.strftime("%Y%m%d%H%M%S")
    log_name = (
        f"{name}_{formatted_date}" if name else formatted_date
    )  # 使用前缀名称命名日志

    _logger.remove()
    # 无控制台打包（windowed）时 sys.stderr 为 None，不能作为 loguru sink
    if sys.stderr is not None:
        _logger.add(sys.stderr, level=print_level, enqueue=True)
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    # enqueue=True：GUI 在子线程写日志时更稳妥；用 str 路径避免个别环境下 Path 异常
    _logger.add(
        str(log_dir / f"{log_name}.log"),
        level=logfile_level,
        enqueue=True,
        encoding="utf-8",
    )
    return _logger


logger = define_log_level()


if __name__ == "__main__":
    logger.info("Starting application")
    logger.debug("Debug message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")

    try:
        raise ValueError("Test error")
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
