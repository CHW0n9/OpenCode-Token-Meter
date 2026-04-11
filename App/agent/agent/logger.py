"""
Shared logger utility for consistent logging across the application.
"""

import os
import datetime
import sys
from .config import BASE_DIR

ERROR_LOG_PATH = os.path.join(BASE_DIR, "error.log")


def _get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _format_log(tag: str, level: str, message: str):
    timestamp = _get_timestamp()
    # Fixed width tag for alignment (10 chars, no brackets)
    tag_part = f"{tag:^10}"
    if level:
        level_part = f"[{level:^8}]"
        return f"{level_part} {timestamp} - {tag_part} {message}"
    return f"{timestamp} - {tag_part} {message}"


def log_info(tag: str, message: str):
    if (
        tag == "Scanner"
        and "0 new files processed, 0 skipped, 0 sessions checked" in message
    ):
        return
    line = _format_log(tag, "INFO", message)
    print(line, flush=True)


def log_warn(tag: str, message: str):
    line = _format_log(tag, "WARN", message)
    print(line, flush=True)


def log_error(tag: str, message: str):
    """Log an error message to terminal and error.log file."""
    line = _format_log(tag, "ERROR", message)
    print(line, flush=True, file=sys.stderr)
    try:
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def log_debug(tag: str, message: str):
    # Only print if DEBUG env var is set or something similar?
    # For now, let's just make it available.
    if os.environ.get("OPENCODE_DEBUG"):
        line = _format_log(tag, "DEBUG", message)
        print(line, flush=True)
