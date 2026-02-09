"""
Read-only database queries for OpenCode Token Meter (parameterized SQL only).
"""
import csv
import os
import sqlite3
import time

from agent.config import DB_PATH


from .utils import DateUtils


def _get_conn():
    if not os.path.exists(DB_PATH):
        # Only print once to avoid spam? Or checking existence is fast.
        # But stats worker calls aggregate repeatedly.
        # Let's print only if it DOESN'T exist or on first connect?
        # Actually, stats_worker runs in a loop.
        # Let's print to stdout, it will be captured.
        # print(f"[DBRead] DB not found at {DB_PATH}", flush=True) 
        return None
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=30, detect_types=sqlite3.PARSE_DECLTYPES)
        return conn
    except Exception as e:
        print(f"[DBRead] Connection failed: {e}", flush=True)
        return None


def _scope_where(scope, conn, timezone="local"):
    if scope == "today":
        return "ts >= ?", [ DateUtils.get_day_start_ts(timezone) ]
    if scope in ("week", "7days"):
        # Align to midnight of 7 days ago (in target timezone)
        now = time.time()
        start_ts = DateUtils.get_day_start_ts(timezone, now - (7 * 24 * 3600))
        return "ts >= ?", [ start_ts ]
    if scope in ("month", "this_month"):
        return "ts >= ?", [ DateUtils.get_month_start_ts(timezone) ]
    if scope == "current_session":
        c = conn.cursor()
        c.execute("SELECT session_id FROM messages ORDER BY ts DESC LIMIT 1")
        row = c.fetchone()
        if not row:
            return "1=0", []
        return "session_id = ?", [ row[0] ]
    if scope in ("all", None, ""):
        return "", []
    return "", []


def _scope_range(scope, conn, timezone="local"):
    now = int(time.time())
    if scope == "today":
        return DateUtils.get_day_start_ts(timezone), now
    if scope in ("week", "7days"):
        # Align to midnight of 7 days ago (in target timezone)
        start_ts = DateUtils.get_day_start_ts(timezone, now - (7 * 24 * 3600))
        return start_ts, now
    if scope in ("month", "this_month"):
        return DateUtils.get_month_start_ts(timezone), now
    if scope == "current_session":
        c = conn.cursor()
        c.execute("SELECT session_id FROM messages ORDER BY ts DESC LIMIT 1")
        row = c.fetchone()
        if not row:
            return now, now
        session_id = row[0]
        c.execute("SELECT MIN(ts) FROM messages WHERE session_id = ?", (session_id,))
        min_row = c.fetchone()
        start = min_row[0] if min_row and min_row[0] else now
        return int(start), now
    if scope in ("all", None, ""):
        c = conn.cursor()
        c.execute("SELECT MIN(ts) FROM messages")
        row = c.fetchone()
        start = row[0] if row and row[0] else now
        # Align to midnight of the start day (local time)
        local_time = time.localtime(start)
        start_of_day = time.struct_time((
            local_time.tm_year,
            local_time.tm_mon,
            local_time.tm_mday,
            0, 0, 0,
            local_time.tm_wday,
            local_time.tm_yday,
            local_time.tm_isdst
        ))
        return int(time.mktime(start_of_day)), now
    return now, now


def _dedup_subquery(where_clause=""):
    base_where = f"WHERE {where_clause}" if where_clause else ""
    return f"""
    (SELECT ts, role, input, output, reasoning, cache_read, cache_write, provider_id, model_id
     FROM messages {base_where}
     GROUP BY ts, role, input, output, reasoning, cache_read, cache_write, provider_id, model_id)
    """


def _dedup_export_subquery(where_clause=""):
    base_where = f"WHERE {where_clause}" if where_clause else ""
    return f"""
    (SELECT
        MIN(session_id) AS session_id,
        MIN(msg_id) AS msg_id,
        ts, role,
        input, output, reasoning, cache_read, cache_write,
        MIN(model) AS model,
        provider_id, model_id
     FROM messages {base_where}
     GROUP BY ts, role, input, output, reasoning, cache_read, cache_write, provider_id, model_id)
    """


def aggregate(scope, timezone="local"):
    """Get aggregate statistics for a scope by converting to range-based query."""
    conn = _get_conn()
    if conn is None:
        return None
    start_ts, end_ts = _scope_range(scope, conn, timezone)
    conn.close()
    return aggregate_range(start_ts, end_ts)


def aggregate_range(start_ts, end_ts):
    conn = _get_conn()
    if conn is None:
        return None
    c = conn.cursor()
    where_clause = "ts >= ? AND ts < ?"
    params = [ start_ts, end_ts ]
    subquery = _dedup_subquery(where_clause)
    token_filter = "(input > 0 OR output > 0 OR reasoning > 0 OR cache_read > 0 OR cache_write > 0)"
    c.execute(f"""
    SELECT
        SUM(input), SUM(output), SUM(reasoning), SUM(cache_read), SUM(cache_write),
        COUNT(CASE WHEN role='assistant' AND {token_filter} THEN 1 END) AS messages,
        COUNT(CASE WHEN role='user' THEN 1 END) AS requests
    FROM {subquery}
    """, params)
    row = c.fetchone()
    conn.close()
    if not row:
        return {
            "input": 0, "output": 0, "reasoning": 0, "cache_read": 0, "cache_write": 0,
            "messages": 0, "requests": 0
        }
    return {
        "input": row[0] or 0,
        "output": row[1] or 0,
        "reasoning": row[2] or 0,
        "cache_read": row[3] or 0,
        "cache_write": row[4] or 0,
        "messages": row[5] or 0,
        "requests": row[6] or 0
    }


def by_provider(scope, timezone="local"):
    """Get stats by provider for a scope by converting to range-based query."""
    conn = _get_conn()
    if conn is None:
        return None
    start_ts, end_ts = _scope_range(scope, conn, timezone)
    conn.close()
    return by_provider_range(start_ts, end_ts)


def by_model(scope, timezone="local"):
    """Get stats by model for a scope by converting to range-based query."""
    conn = _get_conn()
    if conn is None:
        return None
    start_ts, end_ts = _scope_range(scope, conn, timezone)
    conn.close()
    return by_model_range(start_ts, end_ts)


def by_model_range(start_ts, end_ts):
    conn = _get_conn()
    if conn is None:
        return None
    c = conn.cursor()
    where_clause = "ts >= ? AND ts < ?"
    params = [ start_ts, end_ts ]
    subquery = _dedup_subquery(where_clause)
    token_filter = "(input > 0 OR output > 0 OR reasoning > 0 OR cache_read > 0 OR cache_write > 0)"
    c.execute(f"""
    SELECT provider_id, model_id,
           SUM(input), SUM(output), SUM(reasoning),
           SUM(cache_read), SUM(cache_write),
           COUNT(CASE WHEN role='assistant' AND {token_filter} THEN 1 END) AS messages,
           COUNT(CASE WHEN role='user' THEN 1 END) AS requests
    FROM {subquery}
    GROUP BY provider_id, model_id
    """, params)
    result = {}
    for row in c.fetchall():
        provider_id = row[0] or "unknown"
        model_id = row[1] or "unknown"
        if provider_id not in result:
            result[provider_id] = {}
        result[provider_id][model_id] = {
            "input": row[2] or 0,
            "output": row[3] or 0,
            "reasoning": row[4] or 0,
            "cache_read": row[5] or 0,
            "cache_write": row[6] or 0,
            "messages": row[7] or 0,
            "requests": row[8] or 0
        }
    conn.close()
    return result


def by_provider_range(start_ts, end_ts):
    """Get stats by provider for custom time range"""
    conn = _get_conn()
    if conn is None:
        return None
    c = conn.cursor()
    where_clause = "ts >= ? AND ts < ?"
    params = [ start_ts, end_ts ]
    subquery = _dedup_subquery(where_clause)
    token_filter = "(input > 0 OR output > 0 OR reasoning > 0 OR cache_read > 0 OR cache_write > 0)"
    c.execute(f"""
    SELECT provider_id,
           SUM(input), SUM(output), SUM(reasoning),
           SUM(cache_read), SUM(cache_write),
           COUNT(CASE WHEN role='assistant' AND {token_filter} THEN 1 END) AS messages,
           COUNT(CASE WHEN role='user' THEN 1 END) AS requests
    FROM {subquery}
    GROUP BY provider_id
    """, params)
    result = {}
    for row in c.fetchall():
        provider_id = row[0] or "unknown"
        result[provider_id] = {
            "input": row[1] or 0,
            "output": row[2] or 0,
            "reasoning": row[3] or 0,
            "cache_read": row[4] or 0,
            "cache_write": row[5] or 0,
            "messages": row[6] or 0,
            "requests": row[7] or 0
        }
    conn.close()
    return result


def get_raw_trend_data(start_ts, end_ts):
    """
    Fetch raw data for trend calculation in Python.
    Returns: [(ts, provider_id, model_id, input, output, reasoning, requests, cost), ...]
    """
    conn = _get_conn()
    if conn is None:
        return []
    c = conn.cursor()
    where_clause = "ts >= ? AND ts < ?"
    params = [ start_ts, end_ts ]
    subquery = _dedup_subquery(where_clause)
    token_filter = "(input > 0 OR output > 0 OR reasoning > 0 OR cache_read > 0 OR cache_write > 0)"
    
    # We fetch raw rows to bucket them in Python correctly handling timezones
    # Let's adjust the query to fetch necessary columns
    c.execute(f"""
    SELECT
        ts, role, provider_id, model_id,
        input, output, reasoning,
        cache_read, cache_write
    FROM {subquery}
    ORDER BY ts ASC
    """, params)
    
    rows = c.fetchall()
    conn.close()
    return rows


def get_time_range(scope, timezone="local"):
    conn = _get_conn()
    if conn is None:
        now = int(time.time())
        return now, now
    start, end = _scope_range(scope, conn, timezone)
    conn.close()
    return start, end


def export_csv(out_path, scope="month", timezone="local"):
    """Export CSV for a scope by converting to range-based query."""
    conn = _get_conn()
    if conn is None:
        return None
    start_ts, end_ts = _scope_range(scope, conn, timezone)
    conn.close()
    return export_csv_range(out_path, start_ts, end_ts)


def export_csv_range(out_path, start_ts, end_ts):
    out_path = os.path.normpath(out_path)
    if os.path.isdir(out_path):
        filename = f"opencode_tokens_range_{int(time.time())}.csv"
        out_path = os.path.join(out_path, filename)
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    conn = _get_conn()
    if conn is None:
        return None
    c = conn.cursor()
    where_clause = "ts >= ? AND ts < ?"
    params = [ start_ts, end_ts ]
    subquery = _dedup_export_subquery(where_clause)
    c.execute(f"""
    SELECT session_id, msg_id, ts, input, output, reasoning,
           cache_read, cache_write, model, provider_id, model_id, role
    FROM {subquery} ORDER BY ts
    """, params)
    rows = c.fetchall()
    conn.close()

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "session_id", "msg_id", "ts_iso", "role",
            "input", "output", "reasoning",
            "cache_read", "cache_write",
            "model", "provider_id", "model_id"
        ])
        for row in rows:
            session_id, msg_id, ts, input_tok, output_tok, reasoning_tok, cache_r, cache_w = row[:8]
            ts_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))
            model = row[8] if len(row) > 8 else ""
            provider_id = row[9] if len(row) > 9 else ""
            model_id = row[10] if len(row) > 10 else ""
            role = row[11] if len(row) > 11 else ""
            writer.writerow([
                session_id, msg_id, ts_iso, role,
                input_tok, output_tok, reasoning_tok,
                cache_r, cache_w,
                model, provider_id, model_id
            ])
    return out_path
