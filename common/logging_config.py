"""
Global logging configuration for the Snowflake vs Databricks benchmark project.

Provides:
- Colored console output (clean, no auto emojis)
- Separate log files for Snowflake and Databricks
- Centralized logger setup for all modules
- Developers add emojis directly to log messages for major events
"""

import logging
import logging.handlers
from pathlib import Path

try:
    import colorlog
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False


# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def setup_logging():
    """
    Configure global logging with:
    - Colored console output (clean, emojis in messages only)
    - Separate file handlers for Snowflake and Databricks
    - Common file for shared/common logs
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler with colors (no auto-emojis in format)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    if HAS_COLORLOG:
        console_formatter = colorlog.ColoredFormatter(
            fmt="%(log_color)s%(levelname)-8s%(reset)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            reset=True,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
        )
    else:
        console_formatter = logging.Formatter(
            fmt="%(levelname)-8s %(name)s: %(message)s"
        )

    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler for Snowflake logs
    snowflake_file_handler = logging.FileHandler(
        LOGS_DIR / "snowflake.log", mode="a"
    )
    snowflake_file_handler.setLevel(logging.DEBUG)
    snowflake_file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    snowflake_file_handler.setFormatter(snowflake_file_formatter)
    snowflake_file_handler.addFilter(
        _ModuleFilter(["snowflake", "common.connections.snowflake_connection"])
    )
    root_logger.addHandler(snowflake_file_handler)

    # File handler for Databricks logs
    databricks_file_handler = logging.FileHandler(
        LOGS_DIR / "databricks.log", mode="a"
    )
    databricks_file_handler.setLevel(logging.DEBUG)
    databricks_file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    databricks_file_handler.setFormatter(databricks_file_formatter)
    databricks_file_handler.addFilter(
        _ModuleFilter(["databricks", "common.connections.databricks_connection"])
    )
    root_logger.addHandler(databricks_file_handler)

    # File handler for common logs (everything not in platform-specific handlers)
    common_file_handler = logging.FileHandler(LOGS_DIR / "common.log", mode="a")
    common_file_handler.setLevel(logging.DEBUG)
    common_file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    common_file_handler.setFormatter(common_file_formatter)
    common_file_handler.addFilter(
        _ModuleFilter(
            ["common.storage", "common.connections.base_connection"],
            invert=False,
        )
    )
    root_logger.addHandler(common_file_handler)


class _ModuleFilter(logging.Filter):
    """Filter logs based on module names."""

    def __init__(self, module_names, invert=False):
        """
        Args:
            module_names: List of module names to filter on
            invert: If True, matches everything NOT in module_names
        """
        self.module_names = module_names
        self.invert = invert

    def filter(self, record):
        """Return True if record should be logged."""
        matches = any(record.name.startswith(name) for name in self.module_names)
        return not matches if self.invert else matches


# Initialize logging when module is imported
def _init_logging():
    """Initialize logging configuration."""
    setup_logging()


_init_logging()


# Convenience function for getting loggers
def get_logger(name):
    """Get a logger instance for the given module name."""
    logger = logging.getLogger(name)
    return logger
