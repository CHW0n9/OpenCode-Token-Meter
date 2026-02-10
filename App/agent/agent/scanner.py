"""
Scanner for OpenCode message files
"""
import os
import json
import time
from agent.config import MSG_ROOT
from agent.db import insert_message, init_db, get_file_mtime, update_file_mtime
from agent.util import safe_int

class Scanner:
    def __init__(self):
        init_db()
        self.last_scan_time = 0

    def parse_tokens(self, j):
        """
        Parse tokens from JSON with fallback for different formats.
        Returns dict with keys: input, output, reasoning, cache_read, cache_write
        """
        tokens = {
            'input': 0,
            'output': 0,
            'reasoning': 0,
            'cache_read': 0,
            'cache_write': 0
        }
        
        # Try new format first (tokens field)
        if 'tokens' in j:
            t = j['tokens']
            tokens['input'] = safe_int(t.get('input', 0))
            tokens['output'] = safe_int(t.get('output', 0))
            tokens['reasoning'] = safe_int(t.get('reasoning', 0))
            cache = t.get('cache', {})
            tokens['cache_read'] = safe_int(cache.get('read', 0))
            tokens['cache_write'] = safe_int(cache.get('write', 0))
        else:
            # Fallback to usage.* format
            usage = j.get('usage', {})
            tokens['input'] = safe_int(usage.get('prompt_tokens', 0))
            tokens['output'] = safe_int(usage.get('completion_tokens', 0))
            
            comp_details = usage.get('completion_tokens_details', {})
            tokens['reasoning'] = safe_int(comp_details.get('reasoning_tokens', 0))
            
            prompt_details = usage.get('prompt_tokens_details', {})
            tokens['cache_read'] = safe_int(prompt_details.get('cached_tokens', 0))
            tokens['cache_write'] = 0  # Usually not present
        
        return tokens

    def scan_once(self, incremental=True, quick_start=False):
        """
        Perform one scan of message files.
        
        Args:
            incremental: If True, only scan files modified since last scan.
                        If False, scan all files (full scan).
            quick_start: If True, only scan recent sessions (last 7 days).
                        This is useful for fast startup.
        
        Returns count of messages processed.
        """
        start_time = time.time()
        count = 0
        skipped_count = 0
        session_count = 0
        
        if not os.path.isdir(MSG_ROOT):
            print(f"Scan complete: MSG_ROOT not found")
            return count
        
        # Calculate cutoff time for quick_start mode (7 days ago)
        cutoff_time = int(time.time() - 7 * 24 * 3600) if quick_start else 0
        
        scan_mode = "quick" if quick_start else ("incremental" if incremental else "full")
        print(f"Starting {scan_mode} scan...")
        
        # Iterate through all session directories
        for ses in os.listdir(MSG_ROOT):
            ses_dir = os.path.join(MSG_ROOT, ses)
            if not os.path.isdir(ses_dir):
                continue
            
            # Skip non-session directories
            if not ses.startswith('ses_'):
                continue
            
            session_count += 1
            
            # Quick start optimization: check session directory mtime
            if quick_start:
                try:
                    dir_mtime = int(os.path.getmtime(ses_dir))
                    if dir_mtime < cutoff_time:
                        # Session directory not modified in last 7 days, skip it
                        continue
                except:
                    pass
            
            # Iterate through all message files in session
            for fn in os.listdir(ses_dir):
                if not fn.endswith('.json') or not fn.startswith('msg_'):
                    continue
                
                path = os.path.join(ses_dir, fn)
                
                # Get file modification time in ns
                try:
                    file_mtime = os.stat(path).st_mtime_ns
                except Exception:
                    continue
                
                # Quick start optimization: skip old files
                if quick_start and (file_mtime // 1_000_000_000) < cutoff_time:
                    continue
                
                # Check if we should skip this file (incremental scan)
                if incremental:
                    db_mtime = get_file_mtime(path)
                    if db_mtime is not None and db_mtime >= file_mtime:
                        # File hasn't changed, skip it
                        skipped_count += 1
                        continue
                
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        j = json.load(f)
                except Exception as e:
                    # Skip files that can't be parsed
                    continue
                
                # Extract message ID
                msg_id = j.get('id') or j.get('msg_id') or fn.replace('.json', '')
                
                # Extract timestamp (convert ms to seconds if needed)
                ts = 0
                if 'time' in j:
                    if isinstance(j['time'], dict):
                        ts = j['time'].get('created') or j['time'].get('timestamp') or 0
                    else:
                        ts = j['time']
                elif 'timestamp' in j:
                    ts = j['timestamp']
                
                if ts and ts > 1e12:  # Milliseconds -> seconds
                    ts = int(ts / 1000)
                else:
                    ts = int(ts or time.time())
                
                # Parse tokens
                tokens = self.parse_tokens(j)
                
                # Insert into database
                # Try to capture model information if present in message JSON
                model = None
                provider_id = None
                model_id = None
                
                # Try top-level providerID and modelID first (newer format)
                if 'providerID' in j:
                    provider_id = j.get('providerID')
                if 'modelID' in j:
                    model_id = j.get('modelID')
                
                # If not found, try nested model object
                if 'model' in j:
                    if isinstance(j['model'], dict):
                        provider_id = j['model'].get('providerID')
                        model_id = j['model'].get('modelID')
                        # For legacy, also store combined model string
                        model = f"{provider_id}/{model_id}" if provider_id and model_id else None
                    elif isinstance(j['model'], str):
                        model = j['model']
                elif 'meta' in j and isinstance(j['meta'], dict):
                    model = j['meta'].get('model')
                
                # Extract role (user/assistant)
                # If role is not present in JSON, infer from token usage
                role = j.get('role')
                if not role:
                    # Infer: if has token usage, it's likely an assistant response
                    if (tokens['input'] > 0 or tokens['output'] > 0 or 
                        tokens['reasoning'] > 0 or tokens['cache_read'] > 0 or 
                        tokens['cache_write'] > 0):
                        role = 'assistant'
                    else:
                        role = 'user'

                insert_message({
                    'msg_id': msg_id,
                    'session_id': ses,
                    'ts': ts,
                    'input': tokens['input'],
                    'output': tokens['output'],
                    'reasoning': tokens['reasoning'],
                    'cache_read': tokens['cache_read'],
                    'cache_write': tokens['cache_write'],
                    'model': model,
                    'provider_id': provider_id,
                    'model_id': model_id,
                    'role': role,
                })
                
                # Update file mtime in database
                update_file_mtime(path, file_mtime)
                
                count += 1
        
        self.last_scan_time = int(time.time())
        elapsed = time.time() - start_time
        
        print(f"Scan complete: {count} files processed, {skipped_count} skipped, {session_count} sessions checked in {elapsed:.2f}s")
        
        return count
