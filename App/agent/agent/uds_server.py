"""
IPC server for agent (TCP on Windows, UDS on Unix)
"""
import asyncio
import json
import os
import stat
import sys
from agent.config import SOCKET_PATH, USE_TCP, TCP_HOST, TCP_PORT, LOG_PATH
from agent.scanner import Scanner
from agent.db import (aggregate, get_message_count, get_request_count,
                      aggregate_range, get_message_count_range, get_request_count_range,
                      aggregate_by_provider, aggregate_by_model, aggregate_by_model_range)
from agent.exporter import export_csv, export_csv_range
import datetime

def log_message(message: str):
    """Log message to console and BASE_DIR/agent.log"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    print(formatted)
    try:
        with open(LOG_PATH, "a") as f:
            f.write(formatted + "\n")
    except:
        pass

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
        log_message(f"Agent received command: {cmd}")
        response = {"ok": False, "err": "unknown command"}

        if cmd == 'stats':
            scope = req.get('scope', 'today')
            res = aggregate(scope)
            # Compute message count (assistant with tokens) and request count (user messages)
            response = {
                "ok": True,
                "data": {
                    "input": res[0],
                    "output": res[1],
                    "reasoning": res[2],
                    "cache_read": res[3],
                    "cache_write": res[4],
                    "messages": get_message_count(scope),
                    "requests": get_request_count(scope)
                }
            }

        elif cmd == 'refresh':
            # Run incremental scan in executor to avoid blocking
            n = await asyncio.get_event_loop().run_in_executor(
                None, lambda: scanner.scan_once(incremental=True)
            )
            response = {"ok": True, "scanned": n}

        elif cmd == 'export_csv':
            out = req.get('out_path')
            scope = req.get('scope', 'this_month')
            try:
                # Run export in executor
                path = await asyncio.get_event_loop().run_in_executor(
                    None, export_csv, out, scope
                )
                response = {"ok": True, "path": path}
            except Exception as e:
                response = {"ok": False, "err": str(e)}

        elif cmd == 'export_csv_range':
            out = req.get('out_path')
            start_ts = req.get('start_ts')
            end_ts = req.get('end_ts')
            try:
                # Run export in executor
                path = await asyncio.get_event_loop().run_in_executor(
                    None, export_csv_range, out, start_ts, end_ts
                )
                response = {"ok": True, "path": path}
            except Exception as e:
                response = {"ok": False, "err": str(e)}

        elif cmd == 'stats_range':
            start_ts = req.get('start_ts')
            end_ts = req.get('end_ts')
            try:
                res = aggregate_range(start_ts, end_ts)
                response = {
                    "ok": True,
                    "data": {
                        "input": res[0],
                        "output": res[1],
                        "reasoning": res[2],
                        "cache_read": res[3],
                        "cache_write": res[4],
                        "messages": get_message_count_range(start_ts, end_ts),
                        "requests": get_request_count_range(start_ts, end_ts)
                    }
                }
            except Exception as e:
                response = {"ok": False, "err": str(e)}

        elif cmd == 'status':
            response = {
                "ok": True,
                "last_scan": scanner.last_scan_time,
                "uptime": "running"
            }

        elif cmd == 'stats_by_provider':
            scope = req.get('scope', 'today')
            try:
                providers = aggregate_by_provider(scope)
                response = {"ok": True, "data": providers}
            except Exception as e:
                response = {"ok": False, "err": str(e)}

        elif cmd == 'stats_by_model':
            scope = req.get('scope', 'today')
            try:
                models = aggregate_by_model(scope)
                response = {"ok": True, "data": models}
            except Exception as e:
                response = {"ok": False, "err": str(e)}

        elif cmd == 'stats_by_model_range':
            start_ts = req.get('start_ts')
            end_ts = req.get('end_ts')
            try:
                models = aggregate_by_model_range(start_ts, end_ts)
                response = {"ok": True, "data": models}
            except Exception as e:
                response = {"ok": False, "err": str(e)}

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
        log_message(f"Failed to start server: {e}")
        raise

def main():
    """Synchronous entry point for embedded agent server"""
    import asyncio
    from agent.scanner import Scanner
    from agent.db import init_db, migrate_fix_roles
    from agent.config import LOCKFILE_PATH, REFRESH_INTERVAL_SECONDS
    import time

    if os.path.exists(LOCKFILE_PATH):
        try:
            lock_age = time.time() - os.path.getmtime(LOCKFILE_PATH)
            if lock_age < 60:
                print("Agent already running (lockfile exists)", file=sys.stderr)
                return
            else:
                os.remove(LOCKFILE_PATH)
        except:
            pass

    try:
        with open(LOCKFILE_PATH, 'w') as f:
            f.write(str(os.getpid()))
    except Exception as e:
        print(f"Failed to create lockfile: {e}", file=sys.stderr)
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
        log_message("Performing quick start scan (last 7 days)...")
        count = scanner.scan_once(incremental=True, quick_start=True)
        log_message(f"Quick start scan completed: {count} messages indexed")

        loop.run_until_complete(start_server(scanner))
    except Exception as e:
        log_message(f"Critical error in agent main: {e}")
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
