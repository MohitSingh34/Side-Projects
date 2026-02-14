#!/usr/bin/env python3
# log_tracker_test.py (V1.0)
# Simple incremental log tracker (for testing logic of Medha-Core V5)
import os, json, time

ACTIVITY_LOG_PATH = "/tmp/activity_log.json"
CHROME_LOG_PATH = "/tmp/chrome_activity_log.json"
STATE_FILE = "/tmp/log_tracker_state.json"

def load_state():
    """Load last timestamps."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"activity_last_ts": 0, "chrome_last_ts": 0}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def read_json_lines(path):
    """Read all valid JSON lines safely."""
    if not os.path.exists(path):
        return []
    data = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
        return data
    except Exception:
        return []

def show_new_logs(log_file, label, last_ts_key, state):
    separator = f"---------------------{label} logs starting---------------------"
    logs = read_json_lines(log_file)
    if not logs:
        print(f"{separator}\n[Log file empty or missing]")
        return state

    last_ts = state.get(last_ts_key, 0)
    new_entries = [entry for entry in logs if entry.get("timestamp", 0) > last_ts]

    if not new_entries:
        print(f"{separator}\n[No new log entries]")
        return state

    print(separator)
    for entry in new_entries:
        print(json.dumps(entry, ensure_ascii=False))
    print()

    # Update latest timestamp
    state[last_ts_key] = max(e.get("timestamp", 0) for e in new_entries)
    return state

def main():
    print("🧠 Incremental Log Tracker (Test Mode)")
    state = load_state()

    while True:
        state = show_new_logs(CHROME_LOG_PATH, "Chrome", "chrome_last_ts", state)
        state = show_new_logs(ACTIVITY_LOG_PATH, "System", "activity_last_ts", state)
        save_state(state)

        print("⏳ Waiting 12s before next check...\n")
        time.sleep(12)

if __name__ == "__main__":
    main()
