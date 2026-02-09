"""
Utility module for OpenCode Token Meter backend.
Handles timezone-aware date calculations.
"""
import time
import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Backport for older Python versions if needed, though 3.12 has it.
    from datetime import timezone as ZoneInfo

class DateUtils:
    @staticmethod
    def get_timezone(tz_name):
        """Get timezone object from string name"""
        if not tz_name or tz_name.lower() == "local":
            return None # Local system time
        if tz_name.lower() == "utc":
            return datetime.timezone.utc
        try:
            return ZoneInfo(tz_name)
        except Exception:
            return None # Fallback to local on error

    @staticmethod
    def get_day_start_ts(tz_name="local", timestamp=None):
        """Get start of the day timestamp for the given timezone"""
        if timestamp is None:
            timestamp = time.time()
        
        tz = DateUtils.get_timezone(tz_name)
        
        # If local time (tz is None), use localtime
        if tz is None:
            dt = datetime.datetime.fromtimestamp(timestamp)
            start_of_day = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            return int(start_of_day.timestamp())
        
        # Timezone aware
        dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc).astimezone(tz)
        start_of_day = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return int(start_of_day.timestamp())

    @staticmethod
    def get_month_start_ts(tz_name="local", timestamp=None):
        """Get start of the month timestamp for the given timezone"""
        if timestamp is None:
            timestamp = time.time()
            
        tz = DateUtils.get_timezone(tz_name)
        
        if tz is None:
            dt = datetime.datetime.fromtimestamp(timestamp)
            start_of_month = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return int(start_of_month.timestamp())
            
        dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc).astimezone(tz)
        start_of_month = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return int(start_of_month.timestamp())

    @staticmethod
    def get_start_of_day_ts(ts, tz_name="local"):
        """Get start of day for a specific timestamp in given timezone"""
        return DateUtils.get_day_start_ts(tz_name, ts)
    
    @staticmethod
    def align_to_bucket(ts, mode, tz_name="local"):
        """Align timestamp to bucket start (hourly, daily, weekly, monthly)"""
        tz = DateUtils.get_timezone(tz_name)
        
        # Convert timestamp to timezone-aware datetime
        if tz is None:
            dt = datetime.datetime.fromtimestamp(ts)
        else:
            dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).astimezone(tz)
            
        if mode == 'hourly':
            aligned = dt.replace(minute=0, second=0, microsecond=0)
        elif mode == 'daily':
            aligned = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        elif mode == 'weekly':
            # Align to Monday
            days_to_subtract = dt.weekday()
            aligned = dt.replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(days=days_to_subtract)
        elif mode == 'monthly':
            aligned = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            return ts
            
        return int(aligned.timestamp())
