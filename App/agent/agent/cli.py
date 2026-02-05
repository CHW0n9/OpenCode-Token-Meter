"""
CLI tool to interact with the agent via Unix Domain Socket
"""
import socket
import json
import sys
import argparse
from agent.config import USE_TCP, SOCKET_PATH, TCP_HOST, TCP_PORT

def send_request(req, timeout=10):
    """Send a request to the agent and return the response"""
    try:
        if USE_TCP:
            # TCP connection for Windows
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((TCP_HOST, TCP_PORT))
        else:
            # Unix Domain Socket for macOS/Linux
            # Guard AF_UNIX for Windows environment
            af_unix = getattr(socket, "AF_UNIX", None)
            if af_unix is None:
                return {"ok": False, "err": "AF_UNIX not supported on this platform"}
            s = socket.socket(af_unix, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect(SOCKET_PATH)
            
        s.sendall((json.dumps(req) + "\n").encode())
        
        # Read response
        data = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\n" in chunk:
                break
        
        s.close()
        
        # Parse response
        line = data.split(b"\n", 1)[0]
        return json.loads(line.decode())
    
    except socket.timeout:
        return {"ok": False, "err": "timeout"}
    except FileNotFoundError:
        return {"ok": False, "err": "agent not running (socket not found)"}
    except ConnectionRefusedError:
        return {"ok": False, "err": "agent not running (connection refused)"}
    except Exception as e:
        return {"ok": False, "err": str(e)}

def main():
    """CLI main entry point"""
    parser = argparse.ArgumentParser(description='OpenCode Token Meter Agent CLI')
    subparsers = parser.add_subparsers(dest='cmd', help='Command to execute')
    
    # refresh command
    subparsers.add_parser('refresh', help='Trigger a scan refresh')
    
    # stats command
    stats_parser = subparsers.add_parser('stats', help='Get token statistics')
    stats_parser.add_argument('--scope', default='today',
                              choices=['current_session', 'today', '7days', 'month'],
                              help='Time scope for statistics')
    
    # export-csv command
    export_parser = subparsers.add_parser('export-csv', help='Export data to CSV')
    export_parser.add_argument('--out', required=True, help='Output file path')
    export_parser.add_argument('--scope', default='this_month',
                               choices=['all', 'today', '7days', 'this_month'],
                               help='Data scope to export')
    
    # status command
    subparsers.add_parser('status', help='Get agent status')
    
    args = parser.parse_args()
    
    if not args.cmd:
        parser.print_help()
        sys.exit(1)
    
    # Build request
    if args.cmd == 'refresh':
        req = {'cmd': 'refresh'}
    elif args.cmd == 'stats':
        req = {'cmd': 'stats', 'scope': args.scope}
    elif args.cmd == 'export-csv':
        req = {'cmd': 'export_csv', 'out_path': args.out, 'scope': args.scope}
    elif args.cmd == 'status':
        req = {'cmd': 'status'}
    else:
        print(f"Unknown command: {args.cmd}", file=sys.stderr)
        sys.exit(1)
    
    # Send request and print response
    response = send_request(req)
    print(json.dumps(response, indent=2))
    
    # Exit with error code if request failed
    if not response.get('ok'):
        sys.exit(1)

if __name__ == "__main__":
    main()
