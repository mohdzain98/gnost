"""Logger module for the application runtime.
This module defines domain logic, orchestration, and local helper routines.
It keeps responsibilities scoped so other layers can compose behavior safely."""

import logging
from logging import Logger
from typing import Optional


# ANSI color codes for terminal
LEVEL_COLORS = {
    "DEBUG": "\033[36m",  # Cyan
    "INFO": "\033[32m",  # Green
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",  # Red
    "CRITICAL": "\033[35m",  # Magenta
}
RESET_COLOR = "\033[0m"


class ColorFormatter(logging.Formatter):
    """Represent the ColorFormatter component for this domain area.
    It encapsulates related behavior and shared state for callers.
    It is used by higher-level services to keep responsibilities clear."""

    def format(self, record: logging.LogRecord) -> str:
        """Handle format behavior for this component.
        It coordinates inputs, domain rules, and supporting service interactions.
        It returns the expected result and propagates relevant errors clearly."""
        # Build a padded level name so spacing stays consistent
        padded_level = f"{record.levelname + ':':<9}"
        color = LEVEL_COLORS.get(record.levelname, "")
        record.colored_levelname = (
            f"{color}{padded_level}{RESET_COLOR}" if color else padded_level
        )

        # Let the base class format the message (uses colored_levelname)
        return super().format(record)


class AppLogger:
    """Represent the AppLogger component for this domain area.
    It encapsulates related behavior and shared state for callers.
    It is used by higher-level services to keep responsibilities clear."""

    _configured: bool = False

    @classmethod
    def init(cls, level: int = logging.INFO) -> None:
        """Handle init behavior for this component.
        It coordinates inputs, domain rules, and supporting service interactions.
        It returns the expected result and propagates relevant errors clearly."""
        if cls._configured:
            return

        cls._configured = True

        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        # Remove any existing handlers (e.g., Streamlit/basicConfig)
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Console handler with colors
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        console_format = "%(colored_levelname)s %(name)s | %(message)s"
        console_formatter = ColorFormatter(console_format)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    @staticmethod
    def get_logger(name: Optional[str] = None) -> Logger:
        """
        Get a named logger.
        Strips full module path to keep only last segment.
        """
        logger_name = name if name is not None else __name__

        # Keep only last part of dotted path
        short_name = logger_name.split(".")[-1]
        return logging.getLogger(short_name)
