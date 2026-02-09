"""
Configuration for OpenCode Token Meter Agent
"""
import os
import platform

APP_NAME = "OpenCode Token Meter"
SYSTEM = platform.system()

# Platform-specific base directory
if SYSTEM == "Darwin":  # macOS
    BASE_DIR = os.path.join(os.path.expanduser("~"), "Library", "Application Support", APP_NAME)
elif SYSTEM == "Windows":
    # Use APPDATA (Roaming) for user-specific application data
    appdata = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    BASE_DIR = os.path.join(appdata, APP_NAME)
else:  # Linux and other Unix-like systems
    BASE_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", APP_NAME)

os.makedirs(BASE_DIR, exist_ok=True)

DB_PATH = os.path.join(BASE_DIR, "index.db")
LOCKFILE_PATH = os.path.join(BASE_DIR, "agent.lock")
# LOG_PATH = os.path.join(BASE_DIR, "agent.log")

# Message storage root - OpenCode uses .local/share on all platforms including Windows
MSG_ROOT = os.path.join(os.path.expanduser("~"), ".local", "share", "opencode", "storage", "message")

# IPC configuration: Use TCP on Windows, Unix Domain Socket on macOS/Linux
USE_TCP = SYSTEM == "Windows"
TCP_HOST = "127.0.0.1"
TCP_PORT = int(os.environ.get("OPENCODE_AGENT_PORT", "50899"))
SOCKET_PATH = os.path.join(BASE_DIR, "agent.sock")  # Used on Unix systems

REFRESH_INTERVAL_SECONDS = 300  # 5 minutes
TRIGGER_FILE = os.path.join(BASE_DIR, "refresh_trigger")
