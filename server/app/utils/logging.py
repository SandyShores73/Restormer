from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

LOG_FILE_NAME = "restormer-debug.log"
_LOG_FILE_PATH: Optional[Path] = None


def configure_logging(log_dir: Path, *, level: int = logging.INFO) -> Path:
    """Initialise root logging handlers with streamed and rotating file output."""

    global _LOG_FILE_PATH

    log_dir = log_dir.expanduser()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / LOG_FILE_NAME

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    file_handler = RotatingFileHandler(log_path, maxBytes=5_242_880, backupCount=5)
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logging.basicConfig(level=level, handlers=[file_handler, stream_handler], force=True)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)

    _LOG_FILE_PATH = log_path
    return log_path


def get_log_file_path() -> Optional[Path]:
    """Return the path to the configured log file, if initialised."""

    return _LOG_FILE_PATH
