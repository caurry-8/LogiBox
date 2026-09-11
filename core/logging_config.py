import logging
import sys
from pathlib import Path


def _make_stream_safe(stream) -> None:
    """让控制台输出中文时不会因编码问题抛异常或中断日志。

    保留控制台自身的编码（中文 Windows 控制台通常是 GBK，可直接显示中文），
    仅把无法映射的字符替换为 ?，避免 UnicodeEncodeError 打断程序。
    """
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is None:
        return
    try:
        reconfigure(errors="replace")
    except (ValueError, OSError):
        pass


def configure_logging(base_dir: Path) -> logging.Logger:
    logger = logging.getLogger("logibox")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 日志文件固定 UTF-8，保证中文在任何编辑器里都能正确打开。
    try:
        log_dir = base_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "logibox.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        pass

    _make_stream_safe(sys.stdout)
    _make_stream_safe(sys.stderr)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger
