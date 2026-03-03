"""OpenCode Token Meter - WebView UI Module"""
import os
from .main import main

# Read version from VERSION file
def _get_version():
    """Read version from VERSION file in project root"""
    version_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "VERSION")
    try:
        with open(version_file, 'r') as f:
            return f.read().strip()
    except Exception:
        return "1.1.1"  # Fallback version

__version__ = _get_version()
__all__ = ["main"]
