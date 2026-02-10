"""
Shared logger utility for error-only logging
"""
import os
import datetime
from .config import BASE_DIR

ERROR_LOG_PATH = os.path.join(BASE_DIR, "error.log")

def log_error(module: str, message: str):
    """
    Log an error message to the error.log file.
    
    Format: [  MODULE  ] YYYY-MM-DD HH:MM:SS - Message
    """
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Ensure module name is centered in brackets, fixed width of 10 chars for the content
        # internal width 8 chars: "[  API   ]"
        # User requested: "[  API  ]" which looks like 2 spaces padding?
        # Let's try to match the requested format: "[  API  ]"
        # If I use center alignment with width 7 for the name itself?
        # "[{:^7}]".format("API") -> "[  API  ]"
        
        formatted_header = f"[{module:^7}]"
        log_line = f"{formatted_header} {timestamp} - {message}\n"
        
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception:
        # If logging fails, we can't really do much else, maybe print to stderr if possible
        pass
