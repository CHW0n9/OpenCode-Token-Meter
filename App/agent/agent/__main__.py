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
from agent.db import init_db, migrate_fix_roles
from agent.config import REFRESH_INTERVAL_SECONDS, LOCKFILE_PATH

async def periodic_scan(scanner):
    """Periodic background scan task (incremental)"""
    while True:
        try:
            await asyncio.sleep(REFRESH_INTERVAL_SECONDS)
            # Use incremental scan for periodic updates
            await asyncio.get_event_loop().run_in_executor(None, lambda: scanner.scan_once(incremental=True, quick_start=False))
        except Exception as e:
            print(f"Error in periodic scan: {e}", file=sys.stderr)

async def full_history_scan(scanner):
    """One-time full scan of all historical data in background"""
    try:
        # Wait longer before starting full scan to avoid impacting initial UI
        await asyncio.sleep(30)
        print("Starting full history scan in background...")
        count = await asyncio.get_event_loop().run_in_executor(
            None, lambda: scanner.scan_once(incremental=True, quick_start=False)
        )
        print(f"Full history scan completed: {count} new/updated messages processed")
    except Exception as e:
        print(f"Error in full history scan: {e}", file=sys.stderr)

async def main():
    """Main async entry point"""
    # Create lockfile to prevent multiple instances
    if os.path.exists(LOCKFILE_PATH):
        # Check if lockfile is stale (more than 60 seconds old)
        try:
            lock_age = time.time() - os.path.getmtime(LOCKFILE_PATH)
            if lock_age < 60:
                print("Agent already running (lockfile exists)", file=sys.stderr)
                sys.exit(1)
            else:
                # Stale lockfile, remove it
                os.remove(LOCKFILE_PATH)
        except:
            pass
    
    # Create lockfile
    try:
        with open(LOCKFILE_PATH, 'w') as f:
            f.write(str(os.getpid()))
    except Exception as e:
        print(f"Failed to create lockfile: {e}", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Initialize database
        init_db()
        
        # Run migration to fix role fields
        print("Running database migration...")
        fixed_count = migrate_fix_roles()
        if fixed_count > 0:
            print(f"Fixed {fixed_count} messages with NULL role")
        
        # Create scanner
        scanner = Scanner()
        
        # Perform initial QUICK scan (only last 7 days for fast startup)
        print("Performing quick start scan (last 7 days)...")
        count = scanner.scan_once(incremental=True, quick_start=True)
        print(f"Quick start scan completed: {count} messages indexed")
        
        # Start full history scan in background (will scan all old data)
        asyncio.create_task(full_history_scan(scanner))
        
        # Start periodic scan task
        asyncio.create_task(periodic_scan(scanner))
        
        # Start UDS server (this will run forever)
        await start_server(scanner)
    finally:
        # Remove lockfile on exit
        try:
            if os.path.exists(LOCKFILE_PATH):
                os.remove(LOCKFILE_PATH)
        except:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAgent stopped")
        sys.exit(0)
