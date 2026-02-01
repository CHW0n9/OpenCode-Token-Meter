"""
Configuration for OpenCode Token Meter Agent
"""
import os

APP_NAME = "OpenCode Token Meter"
BASE_DIR = os.path.join(os.path.expanduser("~"), "Library", "Application Support", APP_NAME)
os.makedirs(BASE_DIR, exist_ok=True)

DB_PATH = os.path.join(BASE_DIR, "index.db")
SOCKET_PATH = os.path.join(BASE_DIR, "agent.sock")
LOCKFILE_PATH = os.path.join(BASE_DIR, "agent.lock")
MSG_ROOT = os.path.join(os.path.expanduser("~"), ".local", "share", "opencode", "storage", "message")
REFRESH_INTERVAL_SECONDS = 300  # 5 minutes
LOG_PATH = os.path.join(BASE_DIR, "agent.log")
