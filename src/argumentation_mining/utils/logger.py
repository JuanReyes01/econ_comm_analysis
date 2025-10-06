"""
Logger setup utilities for argumentation mining.

Provides functions to configure and initialize loggers with file and console
handlers.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from logging import Logger


def setup_logger(
    name: str = "argumentation_mining",
    log_file: str | Path | None = None,
    level: int = logging.INFO,
    *,
    console: bool = True,
) -> Logger:
    """
    Set up a logger with file and console handlers.

    Args:
        name: Name of the logger.
        log_file: Path to the log file. If None, only console logging
                  will be configured if console is True.
        level: Logging level (default: INFO).
        console: Whether to include console handler (default: True).

    Returns:
        Logger: Configured logger instance.

    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Add file handler if log_file is provided
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Add console handler if requested
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
