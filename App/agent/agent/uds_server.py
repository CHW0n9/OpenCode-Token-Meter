"""
Unix Domain Socket server for agent
"""
import asyncio
import json
import os
import stat
from agent.config import SOCKET_PATH
from agent.scanner import Scanner
from agent.db import (aggregate, get_message_count, get_request_count,
                      aggregate_range, get_message_count_range, get_request_count_range,
                      aggregate_by_provider, aggregate_by_model)
from agent.exporter import export_csv, export_csv_range

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
    """Start the Unix Domain Socket server"""
    # Remove old socket if exists
    if os.path.exists(SOCKET_PATH):
        try:
            os.remove(SOCKET_PATH)
        except:
            pass
    
    # Start server
    server = await asyncio.start_unix_server(
        lambda r, w: handle_client(r, w, scanner),
        path=SOCKET_PATH
    )
    
    # Set socket permissions to 0600 (owner only)
    os.chmod(SOCKET_PATH, stat.S_IRUSR | stat.S_IWUSR)
    
    print(f"Agent listening on {SOCKET_PATH}")
    
    # Use a stop event to allow graceful shutdown via IPC
    global _stop_event
    _stop_event = asyncio.Event()

    print(f"Agent listening on {SOCKET_PATH}")

    # Wait until stop event is set
    try:
        await _stop_event.wait()
        # stop requested: close server and wait for it to finish
        server.close()
        await server.wait_closed()
    finally:
        # Cleanup socket file
        try:
            if os.path.exists(SOCKET_PATH):
                os.remove(SOCKET_PATH)
        except Exception:
            pass
        print("Agent shutting down")
