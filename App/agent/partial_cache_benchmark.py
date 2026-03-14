
import sys
import os
import time
import resource
import gc
import json
import sqlite3

# Add agent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.scanner import Scanner
from agent.db import (
    get_file_mtime, insert_message, update_file_mtime,
    get_all_file_mtimes, insert_messages_batch, update_file_mtimes_batch
)
from agent.config import MSG_ROOT, DB_PATH

def get_db_path():
    return DB_PATH

# --- STAGE 0: ORIGINAL (Individual Operations) ---
class Stage0_Scanner(Scanner):
    def scan_once(self, incremental=True, max_age_days=None, quick_start=False):
        if not os.path.isdir(MSG_ROOT): return 0
        count = 0
        cutoff_time = 0
        if max_age_days: cutoff_time = time.time() - max_age_days*86400

        try:
            with os.scandir(MSG_ROOT) as it:
                for entry in it:
                    if not entry.is_dir() or not entry.name.startswith('ses_'): continue
                    if cutoff_time > 0 and entry.stat().st_mtime < cutoff_time: continue
                    
                    ses_dir = entry.path
                    ses = entry.name
                    try:
                        with os.scandir(ses_dir) as msg_it:
                            for msg_entry in msg_it:
                                if not msg_entry.is_file() or not msg_entry.name.endswith('.json'): continue
                                path = msg_entry.path
                                file_mtime = msg_entry.stat().st_mtime_ns
                                
                                # INDIVIDUAL DB LOOKUP
                                db_mtime = get_file_mtime(path)
                                if db_mtime is not None and db_mtime >= file_mtime: continue
                                
                                # Parse
                                with open(path, 'r', encoding='utf-8') as f: j = json.load(f)
                                tokens = self.parse_tokens(j)
                                msg = {'msg_id': j.get('id', 'test'), 'session_id': ses, 'ts': int(time.time()), **tokens}
                                
                                # INDIVIDUAL DB INSERT
                                insert_message(msg)
                                update_file_mtime(path, file_mtime)
                                count += 1
                    except Exception: pass
        except Exception: pass
        return count

# --- STAGE 3: TIERED + PARTIAL CACHE (Current Logic) ---
class Stage3_Scanner(Scanner):
    pass 

def get_rss_mb():
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return (usage / 1024 / 1024) if sys.platform == 'darwin' else (usage / 1024)

def reset_db():
    db_path = get_db_path()
    if os.path.exists(db_path):
        os.remove(db_path)
    from agent.db import init_db
    init_db()

def measure(label, func, *args, **kwargs):
    gc.collect()
    start_rss = get_rss_mb()
    t0_wall = time.time()
    t0_cpu = time.process_time()
    
    count = func(*args, **kwargs)
    
    t1_cpu = time.process_time()
    t1_wall = time.time()
    end_rss = get_rss_mb()
    
    return {
        'count': count,
        'wall': t1_wall - t0_wall,
        'cpu': t1_cpu - t0_cpu,
        'rss': end_rss
    }

if __name__ == "__main__":
    print(f"Benchmarking Cache Rotation on {len(os.listdir(MSG_ROOT))} sessions...")
    print("-" * 60)
    
    scanners = {
        "Original": Stage0_Scanner(),
        "Tiered+Partial": Stage3_Scanner()
    }
    
    results = []

    for name, scanner in scanners.items():
        print(f"\nTesting {name}...")
        
        # 1. INITIAL SCAN (Empty DB)
        reset_db()
        if hasattr(scanner, 'known_file_mtimes'): del scanner.known_file_mtimes
        
        res_init = measure("Initial (Empty DB, 60d)", scanner.scan_once, incremental=True, max_age_days=60)
        
        # 2. START-APP SCAN (Existing DB, Quick Check, 60d)
        # Verify RAM Peak here (loading 60d cache)
        if hasattr(scanner, 'known_file_mtimes'): del scanner.known_file_mtimes
        if hasattr(scanner, 'cache_days_loaded'): del scanner.cache_days_loaded
        
        res_start = measure("Start-App (60d)", scanner.scan_once, incremental=True, max_age_days=60)
        start_app_rss = res_start['rss']
        
        # 3. INCREMENTAL MONITOR (Loop, 1d)
        # Reuse SAME scanner instance to test cache rotation!
        arg_days = None 
        if name == "Tiered+Partial": arg_days = 1 
        
        incr_walls = []
        incr_cpus = []
        monitor_rss = 0
        
        for i in range(5):
             m = measure("Monitor", scanner.scan_once, incremental=True, max_age_days=arg_days)
             incr_walls.append(m['wall'])
             incr_cpus.append(m['cpu'])
             monitor_rss = m['rss'] # Capture final state
        
        avg_incr_wall = sum(incr_walls)/len(incr_walls)
        avg_incr_cpu = sum(incr_cpus)/len(incr_cpus)
        
        results.append({
            "Strategy": name,
            "Start-App (s)": res_start['wall'],
            "Monitor (s)": avg_incr_wall,
            "RAM Peak (MB)": start_app_rss,
            "RAM Final (MB)": monitor_rss
        })

    print("\n" + "="*80)
    print(f"{'Strategy':<20} | {'Start-App':<10} | {'Monitor':<10} | {'RAM Peak':<10} | {'RAM Final':<10}")
    print("-" * 80)
    for r in results:
        print(f"{r['Strategy']:<20} | {r['Start-App (s)']:<10.4f} | {r['Monitor (s)']:<10.4f} | {r['RAM Peak (MB)']:<10.2f} | {r['RAM Final (MB)']:<10.2f}")
    print("="*80)
