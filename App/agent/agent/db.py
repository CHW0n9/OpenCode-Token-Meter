"""
Database operations for OpenCode Token Meter
"""
import sqlite3
import os
import time
from agent.config import DB_PATH

def get_local_utc_offset():
    """
    Get local UTC offset in seconds.
    Returns positive offset for timezones ahead of UTC (e.g., +28800 for UTC+8)
    """
    if time.localtime().tm_isdst:
        return -time.altzone
    else:
        return -time.timezone

def get_local_day_start_ts():
    """
    Get Unix timestamp for start of today in local timezone.
    Returns UTC timestamp that corresponds to 00:00:00 local time today.
    """
    now = time.time()
    local_time = time.localtime(now)
    # Create struct_time for today at 00:00:00 local
    start_of_day = time.struct_time((
        local_time.tm_year,
        local_time.tm_mon,
        local_time.tm_mday,
        0, 0, 0,  # 00:00:00
        local_time.tm_wday,
        local_time.tm_yday,
        local_time.tm_isdst
    ))
    return int(time.mktime(start_of_day))

def get_conn():
    """Get database connection with WAL mode enabled"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    """Initialize database schema"""
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS files (
      path TEXT PRIMARY KEY,
      mtime INTEGER,
      hash TEXT
    );
    
    CREATE TABLE IF NOT EXISTS messages (
      msg_id TEXT PRIMARY KEY,
      session_id TEXT,
      ts INTEGER,
      input INTEGER,
      output INTEGER,
      reasoning INTEGER,
      cache_read INTEGER,
      cache_write INTEGER,
      model TEXT,
      provider_id TEXT,
      model_id TEXT,
      role TEXT
    );
    
    CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages(ts);
    CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
    CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);
    
    -- Deduplication index for faster model-specific cost calculations
    CREATE INDEX IF NOT EXISTS idx_dedup ON messages(ts, role, input, output, reasoning, cache_read, cache_write, provider_id, model_id);
    """)
    conn.commit()
    conn.close()

def insert_message(msg):
    """Insert or replace a message record"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    INSERT OR REPLACE INTO messages
    (msg_id, session_id, ts, input, output, reasoning, cache_read, cache_write, model, provider_id, model_id, role)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        msg['msg_id'], msg['session_id'], int(msg['ts']),
        int(msg.get('input', 0)), int(msg.get('output', 0)),
        int(msg.get('reasoning', 0)), int(msg.get('cache_read', 0)),
        int(msg.get('cache_write', 0)), msg.get('model'),
        msg.get('provider_id'), msg.get('model_id'), msg.get('role')
    ))
    conn.commit()
    conn.close()

def get_file_mtime(path):
    """Get last modification time of a file from database"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT mtime FROM files WHERE path = ?", (path,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def update_file_mtime(path, mtime):
    """Update or insert file modification time in database"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO files (path, mtime) VALUES (?, ?)", (path, mtime))
    conn.commit()
    conn.close()

def _get_deduplicated_messages_subquery(where_clause=""):
    """
    Generate SQL subquery for deduplicated messages.
    Deduplication is based on: ts, role, input, output, reasoning, cache_read, cache_write, provider_id, model_id
    When duplicates are found, we keep the one with the lexicographically smallest msg_id.
    """
    base_where = f"WHERE {where_clause}" if where_clause else ""
    return f"""
    (SELECT * FROM messages {base_where}
     GROUP BY ts, role, input, output, reasoning, cache_read, cache_write, provider_id, model_id
     HAVING msg_id = MIN(msg_id))
    """

def aggregate(scope):
    """Aggregate token stats by scope (today/7days/month/current_session) with deduplication"""
    conn = get_conn()
    c = conn.cursor()
    
    if scope == "today":
        # Get start of today in local timezone as UTC timestamp
        today_start = get_local_day_start_ts()
        subquery = _get_deduplicated_messages_subquery(f"ts >= {today_start}")
        c.execute(f"""
        SELECT SUM(input), SUM(output), SUM(reasoning), SUM(cache_read), SUM(cache_write)
        FROM {subquery}
        """)
    elif scope == "7days":
        # 7 days ago from start of today
        today_start = get_local_day_start_ts()
        seven_days_ago = today_start - (7 * 24 * 3600)
        subquery = _get_deduplicated_messages_subquery(f"ts >= {seven_days_ago}")
        c.execute(f"""
        SELECT SUM(input), SUM(output), SUM(reasoning), SUM(cache_read), SUM(cache_write)
        FROM {subquery}
        """)
    elif scope == "month":
        # Start of current month in local timezone
        now = time.time()
        local_time = time.localtime(now)
        month_start_struct = time.struct_time((
            local_time.tm_year,
            local_time.tm_mon,
            1,  # First day of month
            0, 0, 0,
            0, 0,
            local_time.tm_isdst
        ))
        month_start = int(time.mktime(month_start_struct))
        subquery = _get_deduplicated_messages_subquery(f"ts >= {month_start}")
        c.execute(f"""
        SELECT SUM(input), SUM(output), SUM(reasoning), SUM(cache_read), SUM(cache_write)
        FROM {subquery}
        """)
    elif scope == "current_session":
        # Get the session with the most recent message
        c.execute("SELECT session_id FROM messages ORDER BY ts DESC LIMIT 1")
        row = c.fetchone()
        if not row:
            conn.close()
            return (0, 0, 0, 0, 0)
        session_id = row[0]
        # For current_session, we use the session_id to filter, then deduplicate
        subquery = _get_deduplicated_messages_subquery(f"session_id='{session_id}'")
        c.execute(f"""
        SELECT SUM(input), SUM(output), SUM(reasoning), SUM(cache_read), SUM(cache_write)
        FROM {subquery}
        """)
    else:
        conn.close()
        return (0, 0, 0, 0, 0)
    
    res = c.fetchone()
    conn.close()
    
    if res and any(res):
        return tuple(x or 0 for x in res)
    return (0, 0, 0, 0, 0)

def get_all_messages(scope='all'):
    """Get all messages for export, optionally filtered by scope"""
    conn = get_conn()
    c = conn.cursor()
    
    if scope == 'this_month':
        # Start of current month in local timezone
        now = time.time()
        local_time = time.localtime(now)
        month_start_struct = time.struct_time((
            local_time.tm_year,
            local_time.tm_mon,
            1,  # First day of month
            0, 0, 0,
            0, 0,
            local_time.tm_isdst
        ))
        month_start = int(time.mktime(month_start_struct))
        c.execute("""
        SELECT session_id, msg_id, ts, input, output, reasoning, cache_read, cache_write, model, provider_id, model_id, role
        FROM messages WHERE ts >= ? ORDER BY ts
        """, (month_start,))
    elif scope == 'today':
        today_start = get_local_day_start_ts()
        c.execute("""
        SELECT session_id, msg_id, ts, input, output, reasoning, cache_read, cache_write, model, provider_id, model_id, role
        FROM messages WHERE ts >= ? ORDER BY ts
        """, (today_start,))
    elif scope == '7days':
        today_start = get_local_day_start_ts()
        seven_days_ago = today_start - (7 * 24 * 3600)
        c.execute("""
        SELECT session_id, msg_id, ts, input, output, reasoning, cache_read, cache_write, model, provider_id, model_id, role
        FROM messages WHERE ts >= ? ORDER BY ts
        """, (seven_days_ago,))
    elif scope == 'current_session':
        # Get the session with the most recent message
        c.execute("SELECT session_id FROM messages ORDER BY ts DESC LIMIT 1")
        row = c.fetchone()
        if not row:
            conn.close()
            return []
        session_id = row[0]
        c.execute("""
        SELECT session_id, msg_id, ts, input, output, reasoning, cache_read, cache_write, model, provider_id, model_id, role
        FROM messages WHERE session_id=? ORDER BY ts
        """, (session_id,))
    else:
        c.execute("""
        SELECT session_id, msg_id, ts, input, output, reasoning, cache_read, cache_write, model, provider_id, model_id, role
        FROM messages ORDER BY ts
        """)
    
    rows = c.fetchall()
    conn.close()
    return rows


def aggregate_range(start_ts, end_ts):
    """Aggregate token stats for custom time range with deduplication"""
    conn = get_conn()
    c = conn.cursor()
    
    where_filter = f"ts >= {start_ts} AND ts < {end_ts}"
    subquery = _get_deduplicated_messages_subquery(where_filter)
    c.execute(f"""
    SELECT SUM(input), SUM(output), SUM(reasoning), SUM(cache_read), SUM(cache_write)
    FROM {subquery}
    """)
    
    res = c.fetchone()
    conn.close()
    
    if res and any(res):
        return tuple(x or 0 for x in res)
    return (0, 0, 0, 0, 0)


def get_all_messages_range(start_ts, end_ts):
    """Get all messages for custom time range"""
    conn = get_conn()
    c = conn.cursor()
    
    c.execute("""
    SELECT session_id, msg_id, ts, input, output, reasoning, cache_read, cache_write, model, provider_id, model_id, role
    FROM messages WHERE ts >= ? AND ts < ? ORDER BY ts
    """, (start_ts, end_ts))
    
    rows = c.fetchall()
    conn.close()
    return rows


def get_message_count_range(start_ts, end_ts):
    """Count assistant messages in custom time range with deduplication"""
    conn = get_conn()
    c = conn.cursor()
    
    token_filter = "(input > 0 OR output > 0 OR reasoning > 0 OR cache_read > 0 OR cache_write > 0)"
    role_filter = "role = 'assistant'"
    where_filter = f"ts >= {start_ts} AND ts < {end_ts} AND {role_filter} AND {token_filter}"
    
    subquery = _get_deduplicated_messages_subquery(where_filter)
    c.execute(f"SELECT COUNT(*) FROM {subquery}")
    
    res = c.fetchone()
    conn.close()
    return res[0] if res else 0


def get_request_count_range(start_ts, end_ts):
    """Count user requests in custom time range with deduplication"""
    conn = get_conn()
    c = conn.cursor()
    
    role_filter = "role = 'user'"
    where_filter = f"ts >= {start_ts} AND ts < {end_ts} AND {role_filter}"
    
    subquery = _get_deduplicated_messages_subquery(where_filter)
    c.execute(f"SELECT COUNT(*) FROM {subquery}")
    
    res = c.fetchone()
    conn.close()
    return res[0] if res else 0


def get_message_count(scope='today'):
    """
    Count assistant messages with actual token usage (role='assistant' and at least one token field > 0).
    This represents response messages that have token costs.
    Uses deduplication to avoid counting duplicate messages across sessions.
    """
    conn = get_conn()
    c = conn.cursor()
    
    # Only count assistant messages where at least one token field is non-zero
    token_filter = "(input > 0 OR output > 0 OR reasoning > 0 OR cache_read > 0 OR cache_write > 0)"
    role_filter = "role = 'assistant'"
    
    if scope == 'today':
        today_start = get_local_day_start_ts()
        where_filter = f"ts >= {today_start} AND {role_filter} AND {token_filter}"
    elif scope == '7days':
        today_start = get_local_day_start_ts()
        seven_days_ago = today_start - (7 * 24 * 3600)
        where_filter = f"ts >= {seven_days_ago} AND {role_filter} AND {token_filter}"
    elif scope == 'month':
        now = time.time()
        local_time = time.localtime(now)
        month_start_struct = time.struct_time((
            local_time.tm_year,
            local_time.tm_mon,
            1,
            0, 0, 0,
            0, 0,
            local_time.tm_isdst
        ))
        month_start = int(time.mktime(month_start_struct))
        where_filter = f"ts >= {month_start} AND {role_filter} AND {token_filter}"
    elif scope == 'current_session':
        c.execute("SELECT session_id FROM messages ORDER BY ts DESC LIMIT 1")
        row = c.fetchone()
        if not row:
            conn.close()
            return 0
        session_id = row[0]
        where_filter = f"session_id='{session_id}' AND {role_filter} AND {token_filter}"
    else:
        where_filter = f"{role_filter} AND {token_filter}"
    
    # Use deduplicated subquery
    subquery = _get_deduplicated_messages_subquery(where_filter)
    c.execute(f"SELECT COUNT(*) FROM {subquery}")
    
    res = c.fetchone()
    conn.close()
    return res[0] if res else 0


def get_request_count(scope='today'):
    """
    Count user requests (role='user').
    This represents the number of user messages/requests.
    Uses deduplication to avoid counting duplicate requests across sessions.
    """
    conn = get_conn()
    c = conn.cursor()
    
    role_filter = "role = 'user'"
    
    if scope == 'today':
        today_start = get_local_day_start_ts()
        where_filter = f"ts >= {today_start} AND {role_filter}"
    elif scope == '7days':
        today_start = get_local_day_start_ts()
        seven_days_ago = today_start - (7 * 24 * 3600)
        where_filter = f"ts >= {seven_days_ago} AND {role_filter}"
    elif scope == 'month':
        now = time.time()
        local_time = time.localtime(now)
        month_start_struct = time.struct_time((
            local_time.tm_year,
            local_time.tm_mon,
            1,
            0, 0, 0,
            0, 0,
            local_time.tm_isdst
        ))
        month_start = int(time.mktime(month_start_struct))
        where_filter = f"ts >= {month_start} AND {role_filter}"
    elif scope == 'current_session':
        c.execute("SELECT session_id FROM messages ORDER BY ts DESC LIMIT 1")
        row = c.fetchone()
        if not row:
            conn.close()
            return 0
        session_id = row[0]
        where_filter = f"session_id='{session_id}' AND {role_filter}"
    else:
        where_filter = role_filter
    
    # Use deduplicated subquery
    subquery = _get_deduplicated_messages_subquery(where_filter)
    c.execute(f"SELECT COUNT(*) FROM {subquery}")
    
    res = c.fetchone()
    conn.close()
    return res[0] if res else 0


def migrate_fix_roles():
    """
    Fix role field for messages where role is NULL.
    Infer role based on token presence:
    - If has token usage (input/output/reasoning > 0) -> 'assistant'
    - Otherwise -> 'user'
    """
    conn = get_conn()
    c = conn.cursor()
    
    # Find all messages with NULL role
    c.execute("SELECT COUNT(*) FROM messages WHERE role IS NULL")
    null_count = c.fetchone()[0]
    
    if null_count == 0:
        conn.close()
        return 0
    
    # Update messages with token usage to 'assistant'
    c.execute("""
    UPDATE messages 
    SET role = 'assistant'
    WHERE role IS NULL 
    AND (input > 0 OR output > 0 OR reasoning > 0 OR cache_read > 0 OR cache_write > 0)
    """)
    
    # Update remaining NULL messages to 'user'
    c.execute("""
    UPDATE messages 
    SET role = 'user'
    WHERE role IS NULL
    """)
    
    conn.commit()
    fixed_count = conn.total_changes
    conn.close()
    
    return fixed_count


def aggregate_by_provider(scope):
    """
    Aggregate token stats grouped by provider_id for a given scope.
    Returns dict[provider_id, stats_dict]
    Uses deduplication to avoid counting duplicate messages across sessions.
    """
    conn = get_conn()
    c = conn.cursor()
    
    # Build WHERE clause based on scope
    if scope == "today":
        today_start = get_local_day_start_ts()
        where_filter = f"ts >= {today_start}"
    elif scope == "7days":
        today_start = get_local_day_start_ts()
        seven_days_ago = today_start - (7 * 24 * 3600)
        where_filter = f"ts >= {seven_days_ago}"
    elif scope == "month":
        now = time.time()
        local_time = time.localtime(now)
        month_start_struct = time.struct_time((
            local_time.tm_year,
            local_time.tm_mon,
            1,
            0, 0, 0,
            0, 0,
            local_time.tm_isdst
        ))
        month_start = int(time.mktime(month_start_struct))
        where_filter = f"ts >= {month_start}"
    elif scope == "current_session":
        # Get the most recent session
        c.execute("SELECT session_id FROM messages ORDER BY ts DESC LIMIT 1")
        row = c.fetchone()
        if not row:
            conn.close()
            return {}
        session_id = row[0]
        where_filter = f"session_id = '{session_id}'"
    else:
        where_filter = "1=1"
    
    # Use deduplicated subquery and aggregate by provider
    subquery = _get_deduplicated_messages_subquery(where_filter)
    token_filter = "(input > 0 OR output > 0 OR reasoning > 0 OR cache_read > 0 OR cache_write > 0)"
    c.execute(f"""
    SELECT provider_id,
           SUM(input), SUM(output), SUM(reasoning),
           SUM(cache_read), SUM(cache_write),
           COUNT(CASE WHEN role='assistant' AND {token_filter} THEN 1 END) as messages,
           COUNT(CASE WHEN role='user' THEN 1 END) as requests
    FROM {subquery}
    GROUP BY provider_id
    """)
    
    result = {}
    for row in c.fetchall():
        provider_id = row[0] or 'unknown'
        result[provider_id] = {
            'input': row[1] or 0,
            'output': row[2] or 0,
            'reasoning': row[3] or 0,
            'cache_read': row[4] or 0,
            'cache_write': row[5] or 0,
            'messages': row[6] or 0,
            'requests': row[7] or 0
        }
    
    conn.close()
    return result


def aggregate_by_model(scope):
    """
    Aggregate token stats grouped by provider_id and model_id for a given scope.
    Returns dict[provider_id, dict[model_id, stats_dict]]
    Uses deduplication to avoid counting duplicate messages across sessions.
    """
    conn = get_conn()
    c = conn.cursor()
    
    # Build WHERE clause based on scope
    if scope == "today":
        today_start = get_local_day_start_ts()
        where_filter = f"ts >= {today_start}"
    elif scope == "7days":
        today_start = get_local_day_start_ts()
        seven_days_ago = today_start - (7 * 24 * 3600)
        where_filter = f"ts >= {seven_days_ago}"
    elif scope == "month":
        now = time.time()
        local_time = time.localtime(now)
        month_start_struct = time.struct_time((
            local_time.tm_year,
            local_time.tm_mon,
            1,
            0, 0, 0,
            0, 0,
            local_time.tm_isdst
        ))
        month_start = int(time.mktime(month_start_struct))
        where_filter = f"ts >= {month_start}"
    elif scope == "current_session":
        # Get the most recent session
        c.execute("SELECT session_id FROM messages ORDER BY ts DESC LIMIT 1")
        row = c.fetchone()
        if not row:
            conn.close()
            return {}
        session_id = row[0]
        where_filter = f"session_id = '{session_id}'"
    else:
        where_filter = "1=1"
    
    # Use deduplicated subquery and aggregate by provider and model
    subquery = _get_deduplicated_messages_subquery(where_filter)
    token_filter = "(input > 0 OR output > 0 OR reasoning > 0 OR cache_read > 0 OR cache_write > 0)"
    c.execute(f"""
    SELECT provider_id, model_id,
           SUM(input), SUM(output), SUM(reasoning),
           SUM(cache_read), SUM(cache_write),
           COUNT(CASE WHEN role='assistant' AND {token_filter} THEN 1 END) as messages,
           COUNT(CASE WHEN role='user' THEN 1 END) as requests
    FROM {subquery}
    GROUP BY provider_id, model_id
    """)
    
    result = {}
    for row in c.fetchall():
        provider_id = row[0] or 'unknown'
        model_id = row[1] or 'unknown'
        
        if provider_id not in result:
            result[provider_id] = {}
        
        result[provider_id][model_id] = {
            'input': row[2] or 0,
            'output': row[3] or 0,
            'reasoning': row[4] or 0,
            'cache_read': row[5] or 0,
            'cache_write': row[6] or 0,
            'messages': row[7] or 0,
            'requests': row[8] or 0
        }
    
    conn.close()
    return result

