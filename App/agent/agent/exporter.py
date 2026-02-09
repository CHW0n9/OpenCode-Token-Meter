"""
CSV export functionality
"""
import csv
import os
import time
from agent.db import (get_all_messages, get_all_messages_range, 
                      _get_deduplicated_messages_subquery, get_conn)

def export_csv(out_path, scope='this_month'):
    """
    Export deduplicated messages to CSV file.
    Returns the output path.
    """
    # If out_path is a directory, create a filename
    if os.path.isdir(out_path):
        filename = f"opencode_tokens_{int(time.time())}.csv"
        out_path = os.path.join(out_path, filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    # Build where clause based on scope (matching db.py logic)
    where_filter = ""
    params = []
    import time as pytime
    from agent.db import get_local_day_start_ts
    
    if scope == 'today':
        where_filter = "ts >= ?"
        params = [get_local_day_start_ts()]
    elif scope == '7days':
        where_filter = "ts >= ?"
        params = [get_local_day_start_ts() - (7 * 24 * 3600)]
    elif scope == 'this_month':
        now = pytime.time()
        local_time = pytime.localtime(now)
        month_start_struct = pytime.struct_time((
            local_time.tm_year, local_time.tm_mon, 1, 0, 0, 0, 0, 0, local_time.tm_isdst
        ))
        where_filter = "ts >= ?"
        params = [int(pytime.mktime(month_start_struct))]
    
    # Get deduplicated messages
    subquery = _get_deduplicated_messages_subquery(where_filter)
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"SELECT session_id, msg_id, ts, input, output, reasoning, cache_read, cache_write, model, provider_id, model_id, role FROM {subquery} ORDER BY ts", params)
    rows = c.fetchall()
    conn.close()
    
    # Write CSV
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'session_id', 'msg_id', 'ts_iso', 'role',
            'input', 'output', 'reasoning',
            'cache_read', 'cache_write', 
            'model', 'provider_id', 'model_id'
        ])

        for row in rows:
            session_id, msg_id, ts, input_tok, output_tok, reasoning_tok, cache_r, cache_w = row[:8]
            ts_iso = pytime.strftime('%Y-%m-%dT%H:%M:%SZ', pytime.gmtime(ts))
            model = row[8] if len(row) > 8 else ''
            provider_id = row[9] if len(row) > 9 else ''
            model_id = row[10] if len(row) > 10 else ''
            role = row[11] if len(row) > 11 else ''
            writer.writerow([
                session_id, msg_id, ts_iso, role,
                input_tok, output_tok, reasoning_tok,
                cache_r, cache_w,
                model, provider_id, model_id
            ])
    
    return out_path


def export_csv_range(out_path, start_ts, end_ts):
    """
    Export deduplicated messages for custom time range to CSV file.
    Returns the output path.
    """
    # Normalize path for Windows
    out_path = os.path.normpath(out_path)

    # If out_path is a directory, create a filename
    if os.path.isdir(out_path):
        filename = f"opencode_tokens_range_{int(time.time())}.csv"
        out_path = os.path.join(out_path, filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    # Get deduplicated messages from database for custom range
    where_filter = "ts >= ? AND ts < ?"
    subquery = _get_deduplicated_messages_subquery(where_filter)
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"SELECT session_id, msg_id, ts, input, output, reasoning, cache_read, cache_write, model, provider_id, model_id, role FROM {subquery} ORDER BY ts", (start_ts, end_ts))
    rows = c.fetchall()
    conn.close()
    
    # Write CSV
    try:
        with open(out_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'session_id', 'msg_id', 'ts_iso', 'role',
                'input', 'output', 'reasoning',
                'cache_read', 'cache_write', 
                'model', 'provider_id', 'model_id'
            ])

            for row in rows:
                session_id, msg_id, ts, input_tok, output_tok, reasoning_tok, cache_r, cache_w = row[:8]
                ts_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(ts))
                model = row[8] if len(row) > 8 else ''
                provider_id = row[9] if len(row) > 9 else ''
                model_id = row[10] if len(row) > 10 else ''
                role = row[11] if len(row) > 11 else ''
                writer.writerow([
                    session_id, msg_id, ts_iso, role,
                    input_tok, output_tok, reasoning_tok,
                    cache_r, cache_w,
                    model, provider_id, model_id
                ])
    except Exception as e:
        raise
    
    return out_path
