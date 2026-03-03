"""
Scanner for OpenCode message files
"""
import os
import json
import time
import sqlite3
from agent.config import MSG_ROOT, OPENCODE_DB_PATH
from agent.db import insert_message, init_db, get_file_mtime, update_file_mtime, mark_failed_requests, get_sync_state, update_sync_state
from agent.util import safe_int
from agent.logger import log_info, log_error

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

    def _sync_from_opencode_db(self):
        """
        Synchronize messages from opencode.db (read-only mode).
        Reads messages from opencode_db_last_ts onward and inserts them into index.db.
        """
        # Check if opencode.db exists
        if not os.path.exists(OPENCODE_DB_PATH):
            log_info("Scanner", "opencode.db not found, skipping sync")
            return
        
        try:
            # Get the last sync timestamp
            last_ts = safe_int(get_sync_state('opencode_db_last_ts', '0'))
            
            # Connect in read-only mode to opencode.db
            conn = sqlite3.connect(f'file:{OPENCODE_DB_PATH}?mode=ro', uri=True)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Query messages updated after last sync
            c.execute(
                "SELECT id, session_id, time_updated, data FROM message WHERE time_updated > ? ORDER BY time_updated ASC",
                (last_ts,)
            )
            
            rows = c.fetchall()
            conn.close()
            
            if not rows:
                log_info("Scanner", "No new messages from opencode.db to sync")
                return
            
            log_info("Scanner", f"Syncing {len(rows)} messages from opencode.db...")
            
            max_ts = last_ts
            messages_to_insert = []
            
            for row in rows:
                try:
                    # Parse the JSON data
                    data = json.loads(row['data'])
                    
                    # Extract timestamp (convert ms to seconds if needed)
                    time_updated = row['time_updated']
                    
                    ts = 0
                    if 'time' in data:
                        if isinstance(data['time'], dict):
                            ts = data['time'].get('created') or data['time'].get('timestamp') or 0
                        else:
                            ts = data['time']
                    elif 'timestamp' in data:
                        ts = data['timestamp']
                    
                    if ts and safe_int(ts) > 1e12:  # Milliseconds -> seconds
                        ts = int(safe_int(ts) / 1000)
                    else:
                        ts = int(safe_int(ts) or time.time())
                    
                    # Parse tokens using existing parse_tokens method
                    tokens = self.parse_tokens(data)
                    
                    # Extract model info
                    model = None
                    provider_id = None
                    model_id = None
                    
                    if 'providerID' in data:
                        provider_id = data.get('providerID')
                    if 'modelID' in data:
                        model_id = data.get('modelID')
                    
                    if 'model' in data:
                        if isinstance(data['model'], dict):
                            provider_id = data['model'].get('providerID')
                            model_id = data['model'].get('modelID')
                            model = f"{provider_id}/{model_id}" if provider_id and model_id else None
                        elif isinstance(data['model'], str):
                            model = data['model']
                    elif 'meta' in data and isinstance(data['meta'], dict):
                        model = data['meta'].get('model')
                    
                    # Infer role
                    role = data.get('role')
                    if not role:
                        if (tokens['input'] > 0 or tokens['output'] > 0 or 
                            tokens['reasoning'] > 0 or tokens['cache_read'] > 0 or 
                            tokens['cache_write'] > 0):
                            role = 'assistant'
                        else:
                            role = 'user'
                    
                    # Add to batch
                    messages_to_insert.append({
                        'msg_id': row['id'],
                        'session_id': row['session_id'],
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

                    if time_updated > max_ts:
                        max_ts = time_updated
                
                except Exception as e:
                    log_error("Scanner", f"Error syncing message {row['id']}: {e}")
                    continue
            
            # Batch insert messages
            if messages_to_insert:
                from agent.db import insert_messages_batch
                insert_messages_batch(messages_to_insert)
                log_info("Scanner", f"Inserted {len(messages_to_insert)} messages from opencode.db")
            
            # Update sync state with max timestamp
            update_sync_state('opencode_db_last_ts', max_ts)
            
        except Exception as e:
            log_error("Scanner", f"Error during opencode.db sync: {e}")

    def scan_once(self, incremental=True, max_age_days=None, quick_start=False):
        """
        Perform one scan of message files.
        
        Args:
            incremental: If True, only scan files modified since last scan.
            max_age_days: If set, only scan session directories from the last N days.
                          (replaces quick_start logic if provided)
            quick_start: Legacy flag. If True, implies max_age_days=7.
        
        Returns count of messages processed.
        """
        start_time = time.time()
        count = 0
        skipped_count = 0
        session_count = 0
        
        if not os.path.isdir(MSG_ROOT):
            log_info("Scanner", "Scan complete: MSG_ROOT not found")
            return count
        
        # Calculate cutoff time
        # quick_start legacy support
        if quick_start and max_age_days is None:
            max_age_days = 7
            
        cutoff_time = 0
        cache_cutoff = None
        if max_age_days is not None:
             cutoff_time = int(time.time() - max_age_days * 24 * 3600)
             cache_cutoff = cutoff_time
        
        scan_mode = f"recent-{max_age_days}d" if max_age_days else ("incremental" if incremental else "full")
        log_info("Scanner", f"Starting {scan_mode} scan (optimized)...")
        
        # 1. Initialize Cache (Lazy Load)
        # 1. Initialize Cache (Lazy Load)
        if not hasattr(self, 'known_file_mtimes'):
             # No cache, load it
             from agent.db import get_all_file_mtimes
             
             # Calculate cutoff
             # cache_cutoff is already calculated above

             self.known_file_mtimes = get_all_file_mtimes(cache_cutoff)
             
             # Track what we loaded
             self.cache_days_loaded = max_age_days
             count_str = f"{len(self.known_file_mtimes)}"
             scope_str = f"{max_age_days} days" if max_age_days else "FULL history"
             log_info("Scanner", f"Initialized cache with {count_str} files (Scope: {scope_str})")
             
        elif max_age_days is not None:
             # We have a cache, but we are requesting a specific restricted scope (e.g. 1 day).
             # Check if we should "rotate" (downgrade) the cache to save RAM.
             # If we currently have a LARGER cache (e.g. 60 days or Full) and want a SMALLER one (1 day),
             # and we are in a repetitive mode (implied by max_age_days usage in monitor loop),
             # we should clear and reload.
             
             should_reload = False
             
             if not hasattr(self, 'cache_days_loaded'):
                 # We have a cache but don't know its size (legacy/full). 
                 # If requesting restricted scope, reload.
                 should_reload = True
             elif self.cache_days_loaded is None:
                 # We have FULL cache, requesting restricted. Reload.
                 should_reload = True
             elif self.cache_days_loaded > max_age_days:
                 # We have 60d cache, requesting 1d. Reload.
                 should_reload = True
                 
             if should_reload:
                 log_info("Scanner", f"Cache Rotation: Downgrading cache from {self.cache_days_loaded if hasattr(self, 'cache_days_loaded') else 'Unknown'}d to {max_age_days}d to save RAM.")
                 # Clear old cache
                 del self.known_file_mtimes
                 # Force garbage collection to reclaim RAM immediately for benchmark visibility
                 import gc
                 gc.collect()
                 
                 from agent.db import get_all_file_mtimes
                 self.known_file_mtimes = get_all_file_mtimes(cache_cutoff)
                 self.cache_days_loaded = max_age_days
                 self.last_cache_reload_ts = time.time()

        # Cache TTL Check for Long-Running Processes
        # If we are in "Monitor Mode" (max_age_days set) and haven't reloaded cache in a while (e.g. 1 hour),
        # force a reload to prune files that have aged out of the window.
        if hasattr(self, 'cache_days_loaded') and self.cache_days_loaded is not None and max_age_days is not None:
             # Only apply TTL if we are in restricted mode
             CACHE_TTL = 3600 # 1 hour
             last_ts = getattr(self, 'last_cache_reload_ts', 0)
             if time.time() - last_ts > CACHE_TTL:
                  log_info("Scanner", f"Cache TTL ({CACHE_TTL}s) expired. Reloading cache to prune old entries...")
                  del self.known_file_mtimes
                  import gc
                  gc.collect()
                  from agent.db import get_all_file_mtimes
                  self.known_file_mtimes = get_all_file_mtimes(cache_cutoff)
                  self.cache_days_loaded = max_age_days
                  self.last_cache_reload_ts = time.time()



        # Import batch functions 
        from agent.db import insert_messages_batch, update_file_mtimes_batch, mark_failed_requests
        
        # Batches for DB operations
        messages_to_insert = []
        files_to_update = []
        
        # Iterate through all session directories
        # os.scandir is faster than os.listdir as it provides file type info without extra stat calls
        try:
            with os.scandir(MSG_ROOT) as it:
                for entry in it:
                    if not entry.is_dir() or not entry.name.startswith('ses_'):
                        continue
                    
                    session_count += 1
                    ses_dir = entry.path
                    ses = entry.name
                    
                    # Filter by date if max_age_days is set
                    if cutoff_time > 0:
                        # Quick start / Max Age optimization: check session directory mtime
                        # Note: Directory mtime changes when files are added/removed.
                        # Ideally we want creation time (st_birthtime on Mac), but mtime is safer for
                        # "active" sessions. If a session was active recently, its dir mtime is recent.
                        try:
                            # entry.stat() is cached by scandir on most platforms
                            dir_stats = entry.stat()
                            dir_mtime = int(dir_stats.st_mtime)
                            
                            if dir_mtime < cutoff_time:
                                # Session directory not modified in last N days, skip it
                                continue
                        except:
                            pass
                    
                    # Iterate through all message files in session
                    try:
                        with os.scandir(ses_dir) as msg_it:
                            for msg_entry in msg_it:
                                if not msg_entry.is_file() or not msg_entry.name.endswith('.json') or not msg_entry.name.startswith('msg_'):
                                    continue
                                
                                path = msg_entry.path
                                fn = msg_entry.name
                                
                                # Get file modification time in ns
                                try:
                                    # Use stat() from entry which might be cached or faster
                                    stat_result = msg_entry.stat()
                                    file_mtime = stat_result.st_mtime_ns
                                except Exception:
                                    continue
                                
                                # Quick start optimization: skip old files
                                if cutoff_time > 0 and (file_mtime // 1_000_000_000) < cutoff_time:
                                    continue
                                
                                # Check if we should skip this file (incremental scan)
                                if incremental:
                                    db_mtime = self.known_file_mtimes.get(path)
                                    if db_mtime is not None and db_mtime >= file_mtime:
                                        # File hasn't changed, skip it
                                        skipped_count += 1
                                        continue
                                
                                try:
                                    with open(path, 'r', encoding='utf-8') as f:
                                        j = json.load(f)
                                except Exception:
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
                                
                                # Extract model info
                                model = None
                                provider_id = None
                                model_id = None
                                
                                if 'providerID' in j:
                                    provider_id = j.get('providerID')
                                if 'modelID' in j:
                                    model_id = j.get('modelID')
                                
                                if 'model' in j:
                                    if isinstance(j['model'], dict):
                                        provider_id = j['model'].get('providerID')
                                        model_id = j['model'].get('modelID')
                                        model = f"{provider_id}/{model_id}" if provider_id and model_id else None
                                    elif isinstance(j['model'], str):
                                        model = j['model']
                                elif 'meta' in j and isinstance(j['meta'], dict):
                                    model = j['meta'].get('model')
                                
                                # Infer role
                                role = j.get('role')
                                if not role:
                                    if (tokens['input'] > 0 or tokens['output'] > 0 or 
                                        tokens['reasoning'] > 0 or tokens['cache_read'] > 0 or 
                                        tokens['cache_write'] > 0):
                                        role = 'assistant'
                                    else:
                                        role = 'user'
                                
                                # Add to batch
                                messages_to_insert.append({
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
                                
                                files_to_update.append((path, file_mtime))
                                # Update in-memory cache immediately
                                self.known_file_mtimes[path] = file_mtime
                                count += 1
                                
                                # Optional: flush batches if they get too large (e.g., > 1000) to avoid memory issues
                                # For now, we'll just process all at the end as datasets usually aren't massive
                                
                    except OSError:
                        pass
                        
        except OSError:
            pass
        
        # 2. Perform batch updates
        if messages_to_insert:
            log_info("Scanner", f"Batch inserting {len(messages_to_insert)} messages...")
            insert_messages_batch(messages_to_insert)
            
        if files_to_update:
            log_info("Scanner", f"Batch updating {len(files_to_update)} file mtimes...")
            update_file_mtimes_batch(files_to_update)
        
        # Sync messages from opencode.db
        self._sync_from_opencode_db()
        
        # Mark failed requests after scanning new messages
        mark_failed_requests()
        
        self.last_scan_time = int(time.time())
        elapsed = time.time() - start_time
        
        log_info("Scanner", f"Scan complete: {count} new files processed, {skipped_count} skipped, {session_count} sessions checked in {elapsed:.2f}s")
        
        return count
