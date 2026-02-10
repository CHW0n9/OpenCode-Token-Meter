import os
import socket
import json
import sys

# Import agent config to use same settings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "agent"))
from agent.config import USE_TCP, SOCKET_PATH, TCP_HOST, TCP_PORT


def _send_request(payload, timeout=5):
    print(f"[DEBUG] Sending request: {payload}")
    data = json.dumps(payload).encode("utf-8") + b"\n"
    
    if USE_TCP:
        # TCP connection for Windows
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((TCP_HOST, TCP_PORT))
            s.sendall(data)
            chunks = []
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
                if b"\n" in chunk:
                    break
            raw = b"".join(chunks).split(b"\n", 1)[0]
    else:
        # Unix Domain Socket for macOS/Linux
        # Guard AF_UNIX for Windows environment
        af_unix = getattr(socket, "AF_UNIX", None)
        if af_unix is None:
            raise RuntimeError("AF_UNIX not supported on this platform")
            
        with socket.socket(af_unix, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect(SOCKET_PATH)
            s.sendall(data)
            chunks = []
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
                if b"\n" in chunk:
                    break
            raw = b"".join(chunks).split(b"\n", 1)[0]
    
    if not raw:
        raise RuntimeError("no response from agent")
    return json.loads(raw.decode("utf-8"))


class AgentClient:
    """Synchronous client wrapper for the agent UDS server."""

    def is_online(self):
        try:
            st = self.get_status()
            return st is not None
        except Exception:
            return False

    def get_status(self):
        try:
            res = _send_request({"cmd": "status"})
            if res.get("ok"):
                return res
        except Exception:
            pass
        return None

    def get_stats(self, scope="today"):
        try:
            res = _send_request({"cmd": "stats", "scope": scope})
            if res.get("ok"):
                return res.get("data")
        except Exception:
            pass
        return None

    def refresh(self):
        try:
            res = _send_request({"cmd": "refresh"})
            return res.get("ok", False)
        except Exception:
            return False

    def export_csv(self, out_path, scope="this_month"):
        try:
            res = _send_request({"cmd": "export_csv", "out_path": out_path, "scope": scope})
            if res.get("ok"):
                return res.get("path")
        except Exception:
            pass
        return None
    
    def export_csv_range(self, out_path, start_ts, end_ts):
        """Export CSV for custom time range"""
        try:
            print(f"[DEBUG] export_csv_range: out_path={out_path}, start={start_ts}, end={end_ts}")
            res = _send_request({"cmd": "export_csv_range", "out_path": out_path, 
                                "start_ts": start_ts, "end_ts": end_ts})
            print(f"[DEBUG] export_csv_range response: {res}")
            if res.get("ok"):
                return res.get("path")
            else:
                print(f"[DEBUG] export_csv_range error: {res.get('err')}")
        except Exception as e:
            print(f"[DEBUG] export_csv_range exception: {e}")
            pass
        return None
    
    def get_stats_range(self, start_ts, end_ts):
        """Get statistics for custom time range"""
        try:
            res = _send_request({"cmd": "stats_range", "start_ts": start_ts, "end_ts": end_ts})
            if res.get("ok"):
                return res.get("data")
        except Exception:
            pass
        return None
    
    def get_stats_by_provider(self, scope="today"):
        """Get statistics grouped by provider"""
        try:
            res = _send_request({"cmd": "stats_by_provider", "scope": scope})
            if res.get("ok"):
                return res.get("data")
        except Exception:
            pass
        return None
    
    def get_stats_by_model(self, scope="today"):
        """Get statistics grouped by provider and model"""
        try:
            res = _send_request({"cmd": "stats_by_model", "scope": scope})
            if res.get("ok"):
                return res.get("data")
        except Exception:
            pass
        return None
    
    def get_stats_by_model_range(self, start_ts, end_ts):
        """Get statistics grouped by provider and model for custom time range"""
        try:
            res = _send_request({"cmd": "stats_by_model_range", "start_ts": start_ts, "end_ts": end_ts})
            if res.get("ok"):
                return res.get("data")
        except Exception:
            pass
        return None

    def shutdown(self):
        try:
            res = _send_request({"cmd": "shutdown"})
            return res.get("ok", False)
        except Exception:
            return False
