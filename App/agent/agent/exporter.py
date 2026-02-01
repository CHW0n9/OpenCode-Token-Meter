"""
CSV export functionality
"""
import csv
import os
import time
from agent.db import get_all_messages, get_all_messages_range

def export_csv(out_path, scope='this_month'):
    """
    Export messages to CSV file.
    Returns the output path.
    """
    # If out_path is a directory, create a filename
    if os.path.isdir(out_path):
        filename = f"opencode_tokens_{int(time.time())}.csv"
        out_path = os.path.join(out_path, filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    # Get messages from database
    rows = get_all_messages(scope)
    
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
            # Row includes: session_id, msg_id, ts, input, output, reasoning, cache_read, cache_write, model, provider_id, model_id, role
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
    
    return out_path


def export_csv_range(out_path, start_ts, end_ts):
    """
    Export messages for custom time range to CSV file.
    Returns the output path.
    """
    # If out_path is a directory, create a filename
    if os.path.isdir(out_path):
        filename = f"opencode_tokens_range_{int(time.time())}.csv"
        out_path = os.path.join(out_path, filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    # Get messages from database for custom range
    rows = get_all_messages_range(start_ts, end_ts)
    
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
    
    return out_path
