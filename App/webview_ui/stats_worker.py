"""
Background stats worker for tray display.
Writes BASE_DIR/tray_stats.json periodically.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from agent.config import BASE_DIR
from backend.settings import Settings, SETTINGS_PATH

try:
    from .backend import db_read
except ImportError:
    # In frozen mode, modules are flattened, so use direct import
    from backend import db_read

STATS_FILE = os.path.join(BASE_DIR, "tray_stats.json")
TAB_SIZE = 8
BASE_LEFT_VALUE_STOP = 2
BASE_RIGHT_LABEL_STOP = 4
BASE_RIGHT_VALUE_STOP = 6


def _log(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[StatsWorker] {timestamp} - {msg}"
    try:
        print(line, flush=True)
    except Exception:
        pass


def _format_tokens(num):
    if num is None:
        return "--"
    try:
        n = int(num)
    except (TypeError, ValueError):
        return "--"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1000:
        return f"{n/1000:.1f}K"
    return str(n)


def _format_cost(value):
    if value is None:
        return "--"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "--"


def _calc_pct(value, threshold):
    try:
        value = float(value)
        threshold = float(threshold)
    except (TypeError, ValueError):
        return 0
    if threshold <= 0:
        return 0
    return min(int((value / threshold) * 100), 999)


def _tab_units(text, tab_size=TAB_SIZE):
    units = 0
    for ch in text:
        if ch == "\t":
            units += tab_size - (units % tab_size)
        else:
            units += 1
    return units


def _tabs_to_target(current_units, target_units, tab_size=TAB_SIZE):
    if current_units < target_units:
        tabs = 0
        units = current_units
        while units < target_units:
            units += tab_size - (units % tab_size)
            tabs += 1
        return max(1, tabs)
    return 1


def _append_tabs(text, target_units, tab_size=TAB_SIZE):
    tabs = _tabs_to_target(_tab_units(text, tab_size), target_units, tab_size)
    return text + ("\t" * tabs)


def _extra_tabs_for_len(length):
    extra = 0
    if length >= 5:
        extra += 1
    if length >= 8:
        extra += 1
    if length >= 11:
        extra += 1
    return extra


def _compute_stops(max_left_len, max_right_len):
    extra_left = _extra_tabs_for_len(max_left_len)
    extra_right = _extra_tabs_for_len(max_right_len)
    left_stop = BASE_LEFT_VALUE_STOP + extra_left
    right_label_stop = BASE_RIGHT_LABEL_STOP + extra_left
    right_value_stop = BASE_RIGHT_VALUE_STOP + extra_left + extra_right
    return left_stop, right_label_stop, right_value_stop


def _build_row(left_label, left_value, right_label, right_value, stops):
    left_stop, right_label_stop, right_value_stop = stops
    text = str(left_label)
    text = _append_tabs(text, TAB_SIZE * left_stop, TAB_SIZE)
    text += str(left_value)
    text = _append_tabs(text, TAB_SIZE * right_label_stop, TAB_SIZE)
    text += str(right_label)
    text = _append_tabs(text, TAB_SIZE * right_value_stop, TAB_SIZE)
    text += str(right_value)
    return text


def _build_display(stats, thresholds_enabled):
    today = stats.get("today", {})
    month = stats.get("month", {})

    today_in = _format_tokens(today.get("input", 0))
    today_req = _format_tokens(today.get("requests", 0))
    today_out = _format_tokens((today.get("output", 0) or 0) + (today.get("reasoning", 0) or 0))
    today_cost = _format_cost(today.get("cost", 0.0))

    month_in = _format_tokens(month.get("input", 0))
    month_req = _format_tokens(month.get("requests", 0))
    month_out = _format_tokens((month.get("output", 0) or 0) + (month.get("reasoning", 0) or 0))
    month_cost = _format_cost(month.get("cost", 0.0))

    row1_stops = _compute_stops(
        max(len(today_in), len(month_in)),
        max(len(today_req), len(month_req))
    )
    cost_today = f"${today_cost}"
    cost_month = f"${month_cost}"
    row2_stops = _compute_stops(
        max(len(today_out), len(month_out)),
        max(len(cost_today), len(cost_month))
    )

    display = {
        "today_row1": _build_row("In:", today_in, "Req:", today_req, row1_stops),
        "today_row2": _build_row("Out:", today_out, "Cost:", cost_today, row2_stops),
        "month_row1": _build_row("In:", month_in, "Req:", month_req, row1_stops),
        "month_row2": _build_row("Out:", month_out, "Cost:", cost_month, row2_stops),
    }

    if thresholds_enabled:
        today_token_pct = f"{today.get('token_pct', 0)}%"
        month_token_pct = f"{month.get('token_pct', 0)}%"
        today_cost_pct = f"{today.get('cost_pct', 0)}%"
        month_cost_pct = f"{month.get('cost_pct', 0)}%"
        row3_stops = _compute_stops(
            max(len(today_token_pct), len(month_token_pct)),
            max(len(today_cost_pct), len(month_cost_pct))
        )
        display["today_row3"] = _build_row("Token:", today_token_pct, "Cost:", today_cost_pct, row3_stops)
        display["month_row3"] = _build_row("Token:", month_token_pct, "Cost:", month_cost_pct, row3_stops)

    return display


def _write_stats_file(payload):
    os.makedirs(BASE_DIR, exist_ok=True)
    tmp_path = STATS_FILE + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        os.replace(tmp_path, STATS_FILE)
        _log(f"wrote stats (today_in={payload['today'].get('input',0)}, month_in={payload['month'].get('input',0)}, month_cost={payload['month'].get('cost',0)})")
    except Exception as exc:
        _log(f"failed to write stats: {exc}")


class WorkerState:
    def __init__(self):
        self.settings = Settings()
        self.last_settings_mtime = 0
        self.pricing_update_id = 0
        self._check_reload()

    def _check_reload(self):
        try:
            mtime = os.path.getmtime(SETTINGS_PATH)
            if mtime > self.last_settings_mtime:
                self.settings.reload()
                self.last_settings_mtime = mtime
                return True
        except Exception:
            pass
        return False

    def get_settings(self):
        return self.settings

    def check_and_reload(self, today_models, month_models):
        """
        Reload settings if changed. 
        Returns True if pricing change AFFECTED cost of today/month models.
        """
        try:
            current_mtime = os.path.getmtime(SETTINGS_PATH)
            if current_mtime <= self.last_settings_mtime:
                return False
            
            # Settings changed!
            # Calculate cost with OLD settings first
            old_today_cost = self.settings.calculate_total_cost(today_models) if today_models else 0.0
            old_month_cost = self.settings.calculate_total_cost(month_models) if month_models else 0.0
            
            # Reload
            _log(f"Reloading settings... (mtime {current_mtime})")
            self.settings.reload()
            self.last_settings_mtime = current_mtime
            
            # Calculate cost with NEW settings
            new_today_cost = self.settings.calculate_total_cost(today_models) if today_models else 0.0
            new_month_cost = self.settings.calculate_total_cost(month_models) if month_models else 0.0
            
            # Check if cost changed
            if abs(new_today_cost - old_today_cost) > 0.000001 or abs(new_month_cost - old_month_cost) > 0.000001:
                self.pricing_update_id += 1
                return True
                
        except Exception as e:
            _log(f"Error checking settings reload: {e}")
        return False

def _collect_stats(worker_state):
    settings = worker_state.get_settings()
    timezone = settings.get("timezone", "local")
    today_stats = db_read.aggregate("today", timezone) or {}
    month_stats = db_read.aggregate("month", timezone) or {}

    today_models = db_read.by_model("today", timezone) or {}
    month_models = db_read.by_model("month", timezone) or {}
    
    # Check for settings update and if it affected cost
    worker_state.check_and_reload(today_models, month_models)
    
    # Recalculate with (potentially new) settings
    today_cost = settings.calculate_total_cost(today_models) if today_models else 0.0
    month_cost = settings.calculate_total_cost(month_models) if month_models else 0.0

    today_tokens = int(today_stats.get("input", 0) or 0) + int(today_stats.get("output", 0) or 0) + int(today_stats.get("reasoning", 0) or 0)
    month_tokens = int(month_stats.get("input", 0) or 0) + int(month_stats.get("output", 0) or 0) + int(month_stats.get("reasoning", 0) or 0)

    thresholds_enabled = bool(settings.get("thresholds.enabled", False))
    daily_token_thresh = settings.get("thresholds.daily_tokens", 1000000)
    daily_cost_thresh = settings.get("thresholds.daily_cost", 20.0)
    monthly_token_thresh = settings.get("thresholds.monthly_tokens", 10000000)
    monthly_cost_thresh = settings.get("thresholds.monthly_cost", 1000.0)

    today_payload = {
        "input": today_stats.get("input", 0),
        "output": today_stats.get("output", 0),
        "reasoning": today_stats.get("reasoning", 0),
        "cache_read": today_stats.get("cache_read", 0),
        "cache_write": today_stats.get("cache_write", 0),
        "requests": today_stats.get("requests", 0),
        "messages": today_stats.get("messages", 0),
        "cost": today_cost,
    }
    month_payload = {
        "input": month_stats.get("input", 0),
        "output": month_stats.get("output", 0),
        "reasoning": month_stats.get("reasoning", 0),
        "cache_read": month_stats.get("cache_read", 0),
        "cache_write": month_stats.get("cache_write", 0),
        "requests": month_stats.get("requests", 0),
        "messages": month_stats.get("messages", 0),
        "cost": month_cost,
    }

    if thresholds_enabled:
        today_payload["token_pct"] = _calc_pct(today_tokens, daily_token_thresh)
        today_payload["cost_pct"] = _calc_pct(today_cost, daily_cost_thresh)
        month_payload["token_pct"] = _calc_pct(month_tokens, monthly_token_thresh)
        month_payload["cost_pct"] = _calc_pct(month_cost, monthly_cost_thresh)

    payload = {
        "timestamp": time.time(),
        "thresholds_enabled": thresholds_enabled,
        "today": today_payload,
        "month": month_payload,
        "thresholds": { # Explicitly pass thresholds for tray comparison
            "daily_tokens": daily_token_thresh,
            "daily_cost": daily_cost_thresh,
            "monthly_tokens": monthly_token_thresh,
            "monthly_cost": monthly_cost_thresh
        },
        "pricing_update_id": worker_state.pricing_update_id
    }
    # _log(f"Thresholds in payload: {payload['thresholds']}")
    payload["display"] = _build_display(payload, thresholds_enabled)
    # Always tell Tray to refresh frequently (e.g. 2s) so it picks up changes immediately.
    # The heavy lifting is done by this worker; reading a JSON file is cheap.
    payload["refresh_interval"] = 2
    
    return payload


    return payload


def main(stop_event=None):
    _log("stats worker starting (smart polling)")
    
    worker_state = WorkerState()
    
    # Path to DB and Trigger
    from agent.config import DB_PATH, BASE_DIR
    TRIGGER_FILE = os.path.join(BASE_DIR, "refresh_trigger")
    
    last_db_mtime = 0
    last_settings_mtime = 0
    
    # Initial run
    try:
        if os.path.exists(DB_PATH):
            last_db_mtime = os.path.getmtime(DB_PATH)
        payload = _collect_stats(worker_state)
        _write_stats_file(payload)
    except Exception as e:
        _log(f"Initial stats collection failed: {e}")

    while True:
        if stop_event and stop_event.is_set():
            _log("stats worker stopping")
            break

        try:
            should_update = False
            
            # 1. Check DB change
            current_db_mtime = 0
            if os.path.exists(DB_PATH):
                current_db_mtime = os.path.getmtime(DB_PATH)
            
            # If WAL mode, main db file might not update mtime? 
            # SQLite WAL usually updates -shm or -wal files. 
            # But usually we can check directory or just main file. 
            # For now, check main file. If wal used, check it too?
            # Let's keep it simple: check main file.
            
            if current_db_mtime > last_db_mtime:
                _log("DB change detected")
                should_update = True
                last_db_mtime = current_db_mtime
                
            # 2. Check Settings change
            # WorkerState handles internal reload logic, but we need to know if we should RUN collect.
            # WorkerState.check_and_reload is called inside collect.
            # We can peek at settings mtime here too.
            settings_mtime = 0
            try:
                if os.path.exists(SETTINGS_PATH):
                    settings_mtime = os.path.getmtime(SETTINGS_PATH)
            except: pass
            
            if settings_mtime > worker_state.last_settings_mtime:
                _log("Settings change detected")
                should_update = True
                # worker_state will update its internal last_mtime when _collect_stats calls it
                
            # 3. Check Manual Trigger
            if os.path.exists(TRIGGER_FILE):
                _log("Manual trigger detected")
                should_update = True
                try:
                    os.remove(TRIGGER_FILE)
                except: pass
            
            if should_update:
                payload = _collect_stats(worker_state)
                # We don't define 'refresh_interval' in payload anymore as it's not fixed
                # But UI might expect it? 
                # Provide a default or what user set, but it won't control client polling
                # since client should also use file watch or just poll fast.
                payload["refresh_interval"] = 0 # 0 could mean "event driven"
                _write_stats_file(payload)
            
            # Sleep small amount to poll for file changes
            # Check stop_event more frequently during sleep if needed, 
            # but 1s is responsive enough
            if stop_event and stop_event.wait(1):
                break
            if not stop_event:
                time.sleep(1)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[StatsWorker] Error scanning messages: {e}")
            import traceback
            traceback.print_exc()
            if stop_event:
                stop_event.wait(5)
            else:
                time.sleep(5)

if __name__ == "__main__":
    main()
