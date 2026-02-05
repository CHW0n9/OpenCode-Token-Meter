import os
import socket
import json


SOCKET_PATH = os.path.expanduser("~/Library/Application Support/OpenCode Token Meter/agent.sock")


def _send_request(payload, timeout=5):
    data = json.dumps(payload).encode("utf-8") + b"\n"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
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
            res = _send_request({"cmd": "export_csv_range", "out_path": out_path, 
                                "start_ts": start_ts, "end_ts": end_ts})
            if res.get("ok"):
                return res.get("path")
        except Exception:
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

    def shutdown(self):
        try:
            res = _send_request({"cmd": "shutdown"})
            return res.get("ok", False)
        except Exception:
            return False
