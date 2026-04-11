#!/usr/bin/env python3
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.expanduser("~/Library/Application Support/OpenCode Token Meter/index.db")

def analyze_messages():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM messages")
    total_messages = c.fetchone()[0]

    c.execute("""
        SELECT COUNT(*)
        FROM messages
        WHERE role = 'assistant'
        AND (input > 0 OR output > 0 OR reasoning > 0 OR cache_read > 0 OR cache_write > 0)
    """)
    assistant_messages = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM messages WHERE role = 'user'")
    user_messages = c.fetchone()[0]

    c.execute("SELECT MIN(ts), MAX(ts) FROM messages")
    min_ts, max_ts = c.fetchone()

    if min_ts is None or max_ts is None:
        print("❌ No messages found in database")
        conn.close()
        return

    min_time = datetime.fromtimestamp(min_ts)
    max_time = datetime.fromtimestamp(max_ts)
    time_span = max_time - min_time

    print("=" * 60)
    print("📊 OpenCode Token Meter - Message Statistics")
    print("=" * 60)
    print(f"\n📅 Time Range:")
    print(f"   Start: {min_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   End:   {max_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Span:  {time_span.days} days, {time_span.seconds // 3600} hours")
    print(f"\n📈 Message Counts:")
    print(f"   Total Messages:     {total_messages:,}")
    print(f"   Assistant Messages: {assistant_messages:,}")
    print(f"   User Messages:      {user_messages:,}")

    print(f"\n🔍 5-Hour Sliding Window Analysis (ALL MESSAGES):")

    window_seconds = 5 * 3600

    c.execute("SELECT ts FROM messages ORDER BY ts")
    timestamps = [row[0] for row in c.fetchall()]

    if not timestamps:
        print("   No timestamps found")
        conn.close()
        return

    max_count = 0
    max_window_start = None
    max_window_end = None

    left = 0
    for right in range(len(timestamps)):
        while timestamps[right] - timestamps[left] > window_seconds:
            left += 1

        current_count = right - left + 1
        if current_count > max_count:
            max_count = current_count
            max_window_start = timestamps[left]
            max_window_end = timestamps[right]

    print(f"   Maximum messages in 5h window: {max_count:,}")
    if max_window_start is not None and max_window_end is not None:
        start_time = datetime.fromtimestamp(max_window_start)
        end_time = datetime.fromtimestamp(max_window_end)
        print(f"   Window: {start_time.strftime('%Y-%m-%d %H:%M:%S')} → {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"\n" + "=" * 60)
    print("📊 OpenCode Token Meter - User Request Statistics")
    print("=" * 60)

    c.execute("SELECT ts FROM messages WHERE role = 'user' ORDER BY ts")
    user_timestamps = [row[0] for row in c.fetchall()]

    if not user_timestamps:
        print("❌ No user requests found in database")
        conn.close()
        return

    user_min_ts = user_timestamps[0]
    user_max_ts = user_timestamps[-1]
    user_min_time = datetime.fromtimestamp(user_min_ts)
    user_max_time = datetime.fromtimestamp(user_max_ts)
    user_time_span = user_max_time - user_min_time

    print(f"\n📅 User Request Time Range:")
    print(f"   Start: {user_min_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   End:   {user_max_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Span:  {user_time_span.days} days, {user_time_span.seconds // 3600} hours")
    print(f"\n📈 User Request Count: {len(user_timestamps):,}")

    print(f"\n🔍 5-Hour Sliding Window Analysis (USER REQUESTS):")

    max_user_count = 0
    max_user_window_start = None
    max_user_window_end = None

    left = 0
    for right in range(len(user_timestamps)):
        while user_timestamps[right] - user_timestamps[left] > window_seconds:
            left += 1

        current_count = right - left + 1
        if current_count > max_user_count:
            max_user_count = current_count
            max_user_window_start = user_timestamps[left]
            max_user_window_end = user_timestamps[right]

    print(f"   Maximum user requests in 5h window: {max_user_count:,}")
    if max_user_window_start is not None and max_user_window_end is not None:
        start_time = datetime.fromtimestamp(max_user_window_start)
        end_time = datetime.fromtimestamp(max_user_window_end)
        print(f"   Window: {start_time.strftime('%Y-%m-%d %H:%M:%S')} → {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"\n📊 5-Hour Window Distribution (USER REQUESTS):")
    windows_over_200 = 0
    windows_over_150 = 0
    windows_over_100 = 0
    windows_over_80 = 0
    windows_over_60 = 0
    windows_over_40 = 0
    windows_over_20 = 0
    total_windows = 0

    left = 0
    for right in range(len(user_timestamps)):
        while user_timestamps[right] - user_timestamps[left] > window_seconds:
            left += 1
        current_count = right - left + 1
        total_windows += 1

        if current_count > 200:
            windows_over_200 += 1
        if current_count > 150:
            windows_over_150 += 1
        if current_count > 100:
            windows_over_100 += 1
        if current_count > 80:
            windows_over_80 += 1
        if current_count > 60:
            windows_over_60 += 1
        if current_count > 40:
            windows_over_40 += 1
        if current_count > 20:
            windows_over_20 += 1

    print(f"   Total 5h windows analyzed: {total_windows:,}")
    print(f"   Windows > 200 requests: {windows_over_200:,} ({windows_over_200/total_windows*100:.2f}%)")
    print(f"   Windows > 150 requests: {windows_over_150:,} ({windows_over_150/total_windows*100:.2f}%)")
    print(f"   Windows > 100 requests: {windows_over_100:,} ({windows_over_100/total_windows*100:.2f}%)")
    print(f"   Windows > 80 requests:  {windows_over_80:,} ({windows_over_80/total_windows*100:.2f}%)")
    print(f"   Windows > 60 requests:  {windows_over_60:,} ({windows_over_60/total_windows*100:.2f}%)")
    print(f"   Windows > 40 requests:  {windows_over_40:,} ({windows_over_40/total_windows*100:.2f}%)")
    print(f"   Windows > 20 requests:  {windows_over_20:,} ({windows_over_20/total_windows*100:.2f}%)")
    print(f"   Windows ≤ 20 requests:  {total_windows - windows_over_20:,} ({(total_windows - windows_over_20)/total_windows*100:.2f}%)")

    print(f"\n🔥 Non-Overlapping High-Activity 5h Windows (USER REQUESTS):")
    print(f"   (Each peak excludes ±5h around its center)")

    all_windows = []
    left = 0
    for right in range(len(user_timestamps)):
        while user_timestamps[right] - user_timestamps[left] > window_seconds:
            left += 1
        current_count = right - left + 1
        window_start = user_timestamps[left]
        window_end = user_timestamps[right]
        window_center = (window_start + window_end) / 2
        all_windows.append((current_count, window_start, window_end, window_center))

    all_windows.sort(reverse=True, key=lambda x: x[0])

    selected_windows = []
    excluded_ranges = []

    for count, start, end, center in all_windows:
        overlap = False
        for excl_start, excl_end in excluded_ranges:
            if not (end < excl_start or start > excl_end):
                overlap = True
                break

        if not overlap:
            selected_windows.append((count, start, end, center))
            excluded_start = center - window_seconds
            excluded_end = center + window_seconds
            excluded_ranges.append((excluded_start, excluded_end))

    for i, (count, start_ts, end_ts, center_ts) in enumerate(selected_windows[:15], 1):
        start_time = datetime.fromtimestamp(start_ts)
        end_time = datetime.fromtimestamp(end_ts)
        center_time = datetime.fromtimestamp(center_ts)
        rate = count / 5
        print(f"   {i}. {count:,} requests ({rate:.1f}/h)")
        print(f"      Center: {center_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"      Window: {start_time.strftime('%Y-%m-%d %H:%M:%S')} → {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

    total_hours = (user_max_ts - user_min_ts) / 3600
    avg_per_hour = len(user_timestamps) / total_hours if total_hours > 0 else 0
    print(f"\n📊 Average Rate (USER REQUESTS):")
    print(f"   {avg_per_hour:.2f} requests/hour")

    total_days = (user_max_ts - user_min_ts) / 86400
    avg_per_day = len(user_timestamps) / total_days if total_days > 0 else 0
    print(f"   {avg_per_day:.2f} requests/day")

    print("\n" + "=" * 60)

    conn.close()

if __name__ == "__main__":
    analyze_messages()
