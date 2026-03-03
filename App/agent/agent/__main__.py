"""
Main entry point for the agent
"""
import asyncio
import sys
import os
import time
# Use absolute imports so the frozen executable can import modules correctly
from agent.scanner import Scanner
from agent.uds_server import start_server
from agent.db import init_db, migrate_fix_roles, is_db_populated
from agent.config import REFRESH_INTERVAL_SECONDS, LOCKFILE_PATH
from agent.logger import log_info, log_error

async def periodic_scan(scanner, stop_event):
    """
    Periodic background scan task with dynamic interval
    - Fast Mode: 30s interval (default start)
    - Slow Mode: 300s interval (after 10 scans with no updates)
    """
    FAST_INTERVAL = 30
    SLOW_INTERVAL = 300
    TRANSITION_THRESHOLD = 10  # number of empty scans before switching to slow mode
    
    current_interval = FAST_INTERVAL
    no_update_count = 0
    
    log_info("Agent", f"Starting periodic scan in FAST mode ({FAST_INTERVAL}s)")
    
    while not stop_event.is_set():
        try:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=current_interval)
                # If we get here, stop_event is set, exit loop
                log_info("Agent", "Periodic scan stopping...")
                break
            except asyncio.TimeoutError:
                # Timeout triggered, time to scan
                pass
            
            # Run scan
            # parse count from return value if possible, currently lambda returns it
            
            # TIERED SCANNING STRATEGY
            # Default: Scan last 1 day (Rapid Monitor) as requested.
            
            scan_kwargs = {
                'incremental': True,
                'max_age_days': 1, # Always scan last 24h only
                'quick_start': False
            }
            
            count = await asyncio.get_event_loop().run_in_executor(
                None, lambda: scanner.scan_once(**scan_kwargs)
            )
            
            if count > 0:
                # Activity detected
                if current_interval != FAST_INTERVAL:
                    log_info("Agent", f"Activity detected ({count} new). Switching to FAST mode ({FAST_INTERVAL}s)")
                current_interval = FAST_INTERVAL
                no_update_count = 0
                
                # If we found activity in a quick scan, maybe force a deep scan soon? 
                # Not necessarily, the quick scan caught it.
            else:
                # No activity
                no_update_count += 1
                
                # Check if we should switch to slow mode
                if current_interval == FAST_INTERVAL and no_update_count >= TRANSITION_THRESHOLD:
                    log_info("Agent", f"No activity for {TRANSITION_THRESHOLD} scans. Switching to SLOW mode ({SLOW_INTERVAL}s)")
                    current_interval = SLOW_INTERVAL
                    no_update_count = 0  # Reset counter (not strictly needed for slow mode but clean)
                    
        except asyncio.CancelledError:
            log_info("Agent", "Periodic scan cancelled")
            break
        except Exception as e:
            log_error("Scanner", f"Error in periodic scan: {e}")
            # On error, fallback to slow interval to avoid tight error loops
            # We use sleep here but check stop_event periodically if needed, 
            # or just simple sleep since it's error case
            await asyncio.sleep(SLOW_INTERVAL)

async def full_history_scan():
    """One-time full scan of all historical data in background"""
    try:
        # Wait longer before starting full scan to avoid impacting initial UI
        await asyncio.sleep(30)
        print("Starting full history scan in background...")
        
        # Use a FRESH scanner instance to avoid concurrency/locking issues with the main loop
        from agent.scanner import Scanner
        bg_scanner = Scanner()
        
        count = await asyncio.get_event_loop().run_in_executor(
            None, lambda: bg_scanner.scan_once(incremental=True, quick_start=False)
        )
        log_info("Agent", f"Full history scan completed: {count} new/updated messages processed")
    except Exception as e:
        log_error("Scanner", f"Error in full history scan: {e}")

def _is_pid_running(pid):
    if pid is None:
        return False
    try:
        if sys.platform == "win32":
            import subprocess
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return str(pid) in result.stdout
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _read_lock_pid(path):
    try:
        with open(path, "r") as f:
            return int(f.read().strip())
    except Exception:
        return None


async def main(threading_stop_event=None):
    """Main async entry point"""
    # Create lockfile to prevent multiple instances
    if os.path.exists(LOCKFILE_PATH):
        pid = _read_lock_pid(LOCKFILE_PATH)
        if _is_pid_running(pid):
            log_error("Agent", "Agent already running (lockfile exists)")
            sys.exit(1)
        try:
            os.remove(LOCKFILE_PATH)
        except Exception:
            pass
    
    # Create lockfile
    try:
        with open(LOCKFILE_PATH, 'w') as f:
            f.write(str(os.getpid()))
    except Exception as e:
        log_error("Agent", f"Failed to create lockfile: {e}")
        sys.exit(1)
    
    try:
        # Check if DB is populated (before init may change things?)
        # init_db() ensures tables exist, which is needed for is_db_populated
        init_db()
        
        # Check if we have any data
        has_data = is_db_populated()
        
        # Run migration to fix role fields
        log_info("Agent", "Running database migration...")
        fixed_count = migrate_fix_roles()
        if fixed_count > 0:
            log_info("Agent", f"Fixed {fixed_count} messages with NULL role")
        
        # Create scanner
        scanner = Scanner()
        
        if not has_data:
            log_info("Agent", "Fresh database detected. Performing FULL initial scan of all messages...")
            # For fresh install, we must scan everything to have correct stats
            # This might take a moment but ensures accuracy
            count = scanner.scan_once(incremental=True, quick_start=False)
            log_info("Agent", f"Full initial scan completed: {count} messages indexed")
        else:
            # Perform initial QUICK scan (last 60 days / 2 months)
            log_info("Agent", "Performing quick start scan (last 60 days)...")
            count = scanner.scan_once(incremental=True, max_age_days=60)
            log_info("Agent", f"Quick start scan completed: {count} messages indexed")
            
            # Schedule a background FULL scan explicitly as requested by user
            # Start background full history scan (one-off)
            # This runs independently to catch any historical checks without blocking the main loop
            asyncio.create_task(full_history_scan())
        
        # Shared event to signal shutdown
        stop_event = asyncio.Event()

        # If running in a thread with a threading.Event, monitor it
        if threading_stop_event:
            async def monitor_threading_event():
                while not threading_stop_event.is_set():
                    await asyncio.sleep(1)
                log_info("Agent", "Threading stop event detected, shutting down agent...")
                stop_event.set()
                # Also need to stop server? server task waits on stop_event, so it should be fine.
            
            asyncio.create_task(monitor_threading_event())
        
        # Start periodic scan task
        scan_task = asyncio.create_task(periodic_scan(scanner, stop_event))
        
        # Start UDS server (this will run forever until cancelled)
        try:
            await start_server(scanner)
        except asyncio.CancelledError:
            pass
        finally:
            log_info("Agent", "Stopping agent...")
            stop_event.set()
            # Wait for scan task to finish current iteration if needed
            if not scan_task.done():
                scan_task.cancel()
                try:
                    await scan_task
                except asyncio.CancelledError:
                    pass
            
    finally:
        # Remove lockfile on exit
        try:
            if os.path.exists(LOCKFILE_PATH):
                # Only remove if it contains our PID
                if _read_lock_pid(LOCKFILE_PATH) == os.getpid():
                    os.remove(LOCKFILE_PATH)
        except Exception:
            pass
            if os.path.exists(LOCKFILE_PATH):
                os.remove(LOCKFILE_PATH)
        except:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log_info("Agent", "Agent stopped via KeyboardInterrupt")
        sys.exit(0)
