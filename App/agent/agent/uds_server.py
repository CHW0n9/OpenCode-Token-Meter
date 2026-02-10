"""
IPC server for agent (TCP on Windows, UDS on Unix)
"""
import asyncio
import json
import os
import stat
import sys
from agent.config import SOCKET_PATH, USE_TCP, TCP_HOST, TCP_PORT
from agent.scanner import Scanner
from agent.db import init_db, migrate_fix_roles
from agent.logger import log_error
import datetime

def log_message(message: str):
    """Log message to console (File logging DISABLED)"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    # print(formatted)
    # try:
    #     with open(LOG_PATH, "a") as f:
    #         f.write(formatted + "\n")
    # except:
    #     pass

# Event used to signal server shutdown from a client command
_stop_event = None

async def handle_client(reader, writer, scanner):
    """Handle a single client connection"""
    try:
        line = await reader.readline()
        if not line:
            writer.close()
            return
        
        try:
            req = json.loads(line.decode())
        except Exception:
            writer.write(b'{"ok":false,"err":"invalid request"}\n')
            await writer.drain()
            writer.close()
            return
        
        cmd = req.get('cmd')
        # log_message(f"Agent received command: {cmd}")
        response = {"ok": False, "err": "unknown command"}
        
        if cmd == 'refresh':
            # Run incremental scan in executor to avoid blocking
            n = await asyncio.get_event_loop().run_in_executor(
                None, lambda: scanner.scan_once(incremental=True)
            )
            response = {"ok": True, "scanned": n}
        elif cmd == 'status':
            response = {
                "ok": True,
                "last_scan": scanner.last_scan_time,
                "uptime": "running"
            }
        elif cmd == 'shutdown':
            # Gracefully request the agent to stop
            response = {"ok": True, "msg": "shutting down"}
            try:
                if _stop_event is not None:
                    _stop_event.set()
            except Exception:
                pass
        
        writer.write((json.dumps(response) + "\n").encode())
        await writer.drain()
    
    except Exception as e:
        try:
            writer.write((json.dumps({"ok": False, "err": str(e)}) + "\n").encode())
            await writer.drain()
        except:
            pass
    
    finally:
        writer.close()

async def start_server(scanner):
    """Start the IPC server (TCP on Windows, UDS on Unix)"""
    try:
        if USE_TCP:
            # TCP server for Windows
            server = await asyncio.start_server(
                lambda r, w: handle_client(r, w, scanner),
                host=TCP_HOST,
                port=TCP_PORT
            )
            log_message(f"Agent listening on {TCP_HOST}:{TCP_PORT} (TCP)")
        else:
            # Unix Domain Socket for macOS/Linux
            if os.path.exists(SOCKET_PATH):
                try:
                    os.remove(SOCKET_PATH)
                except:
                    pass
            
            # Use start_unix_server for Unix Domain Sockets
            server = await asyncio.start_unix_server(
                lambda r, w: handle_client(r, w, scanner),
                path=SOCKET_PATH
            )
            
            try:
                os.chmod(SOCKET_PATH, stat.S_IRUSR | stat.S_IWUSR)
            except:
                pass
            
            log_message(f"Agent listening on {SOCKET_PATH} (UDS)")
        
        global _stop_event
        _stop_event = asyncio.Event()

        try:
            await _stop_event.wait()
            server.close()
            await server.wait_closed()
        finally:
            if not USE_TCP:
                try:
                    if os.path.exists(SOCKET_PATH):
                        os.remove(SOCKET_PATH)
                except:
                    pass
            log_message("Agent server stopped")

    except Exception as e:
        log_error("Agent", f"Failed to start server: {e}")
        raise

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


def main():
    """Synchronous entry point for embedded agent server"""
    import asyncio
    from agent.scanner import Scanner
    from agent.config import LOCKFILE_PATH
    
    if os.path.exists(LOCKFILE_PATH):
        pid = _read_lock_pid(LOCKFILE_PATH)
        if _is_pid_running(pid):
            log_error("Agent", "Agent already running (lockfile exists)")
            return
        try:
            os.remove(LOCKFILE_PATH)
        except Exception:
            pass
    
    try:
        with open(LOCKFILE_PATH, 'w') as f:
            f.write(str(os.getpid()))
    except Exception as e:
        log_error("Agent", f"Failed to create lockfile: {e}")
        return
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        init_db()
        log_message("Running database migration...")
        fixed_count = migrate_fix_roles()
        if fixed_count > 0:
            log_message(f"Fixed {fixed_count} messages with NULL role")
        
        scanner = Scanner()
        from agent.db import is_db_populated
        
        if not is_db_populated():
            log_message("Database empty or not populated. Performing FULL INITIAL SCAN...")
            # Full scan: incremental=False, quick_start=False
            count = scanner.scan_once(incremental=False, quick_start=False)
            log_message(f"Full initial scan completed: {count} messages indexed")
        else:
            log_message("Performing quick start scan (last 7 days)...")
            count = scanner.scan_once(incremental=True, quick_start=True)
            log_message(f"Quick start scan completed: {count} messages indexed")
        
        loop.run_until_complete(start_server(scanner))
    except Exception as e:
        log_error("Agent", f"Critical error in agent main: {e}")
    finally:
        try:
            loop.close()
        except:
            pass
        try:
            if os.path.exists(LOCKFILE_PATH):
                os.remove(LOCKFILE_PATH)
        except:
            pass
