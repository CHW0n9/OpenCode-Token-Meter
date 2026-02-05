"""
Utility functions
"""

def safe_int(val, default=0):
    """Safely convert value to int, return default if fails"""
    try:
        return int(val) if val is not None else default
    except (ValueError, TypeError):
        return default
