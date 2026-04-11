"""Bridge to communicate with the background agent"""
import json
import socket
import os
import sys

# Import agent config
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "agent"))
from agent.config import USE_TCP, SOCKET_PATH, TCP_HOST, TCP_PORT


class AgentBridge:
    """Bridge to communicate with agent via UDS/TCP"""
    
    def __init__(self):
        self.timeout = 5
    
    def _send_request(self, payload):
        """Send request to agent and return response"""
        data = json.dumps(payload).encode("utf-8") + b"\n"
        
        if USE_TCP:
            # TCP for Windows
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(self.timeout)
                s.connect((TCP_HOST, TCP_PORT))
                s.sendall(data)
                return self._receive_response(s)
        else:
            # Unix Domain Socket for macOS/Linux
            af_unix = getattr(socket, "AF_UNIX", None)
            if af_unix is None:
                raise RuntimeError("AF_UNIX not supported on this platform")
            
            with socket.socket(af_unix, socket.SOCK_STREAM) as s:
                s.settimeout(self.timeout)
                s.connect(SOCKET_PATH)
                s.sendall(data)
                return self._receive_response(s)
    
    def _receive_response(self, sock):
        """Receive response from socket"""
        chunks = []
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
            if b"\n" in chunk:
                break
        raw = b"".join(chunks).split(b"\n", 1)[0]
        if not raw:
            raise RuntimeError("No response from agent")
        return json.loads(raw.decode("utf-8"))
    
    # Agent API methods
    def get_status(self):
        res = self._send_request({"cmd": "status"})
        return res if res.get("ok") else None

    def refresh(self):
        res = self._send_request({"cmd": "refresh"})
        return res.get("ok", False)
    
    def shutdown(self):
        res = self._send_request({"cmd": "shutdown"})
        return res.get("ok", False)
