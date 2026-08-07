from __future__ import annotations

import logging
import sys
from typing import Any

from app.core.config import settings

_CONFIGURED = False

_LOGGER_LEVEL = logging.INFO
if settings.DEBUG:
    _LOGGER_LEVEL = logging.DEBUG


def _configure() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(_LOGGER_LEVEL)
    # Quiet noisy third-party loggers.
    for noisy in ("httpx", "httpcore", "qdrant_client", "urllib3", "multipart"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    _configure()
    return logging.getLogger(name)


def log_struct(logger: logging.Logger, level: str, event: str, **fields: Any) -> None:
    _configure()
    msg = f"[{event}] " + " ".join(f"{k}={v}" for k, v in fields.items())
    getattr(logger, level)(msg)
