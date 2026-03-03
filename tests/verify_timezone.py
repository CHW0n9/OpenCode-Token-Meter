import sys
import os
import time
import datetime
import unittest

# Add path to backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'App', 'webview_ui', 'backend')))

from utils import DateUtils

class TestDateUtils(unittest.TestCase):
    def test_get_timezone(self):
        self.assertIsNone(DateUtils.get_timezone("local"))
        self.assertEqual(DateUtils.get_timezone("UTC"), datetime.timezone.utc)
        self.assertIsNotNone(DateUtils.get_timezone("Asia/Hong_Kong"))

    def test_day_start_utc(self):
        # 2023-10-27 12:00:00 UTC
        ts = 1698408000 
        
        # Start of day UTC should be 1698364800 (2023-10-27 00:00:00 UTC)
        start_ts = DateUtils.get_day_start_ts("UTC", ts)
        self.assertEqual(start_ts, 1698364800)
        
    def test_day_start_hk(self):
        # 2023-10-27 12:00:00 UTC = 20:00:00 HK
        ts = 1698408000
        
        # Start of day HK should be 2023-10-27 00:00:00 HK
        # 2023-10-27 00:00:00 HK = 2023-10-26 16:00:00 UTC = 1698336000
        start_ts = DateUtils.get_day_start_ts("Asia/Hong_Kong", ts)
        self.assertEqual(start_ts, 1698336000)

    def test_bucket_alignment_daily_utc(self):
        ts = 1698408000 # 2023-10-27 12:00:00 UTC
        aligned = DateUtils.align_to_bucket(ts, 'daily', 'UTC')
        self.assertEqual(aligned, 1698364800)

    def test_bucket_alignment_daily_hk(self):
        ts = 1698408000 # 2023-10-27 20:00:00 HK
        aligned = DateUtils.align_to_bucket(ts, 'daily', 'Asia/Hong_Kong')
        # Should be 00:00 HK = 1698336000
        self.assertEqual(aligned, 1698336000)

if __name__ == '__main__':
    unittest.main()
