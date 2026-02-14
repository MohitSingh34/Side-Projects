#!/usr/bin/env python3
# log_server.py (V6.7 - Meaningful Change Incremental Server)
# Sends only entries that meaningfully changed since last request.
# Ignores routine field updates like active_for or last_update.

from flask import Flask, jsonify
from flask_cors import CORS
import os, json, time, atexit, signal, hashlib, tempfile

app = Flask(__name__)
CORS(app)

SERVER_PORT = 5002
CHROME_LOG_PATH = "/tmp/chrome_activity_log.json"
ACTIVITY_LOG_PATH = "/tmp/activity_log.json"
STATE_FILE = "/tmp/log_server_state.json"

# ---------------- STATE HANDLING ----------------
def load_state():
    """Load saved state or create fresh."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                s = json.load(f)
            if "chrome_hashes" not in s: s["chrome_hashes"] = {}
            if "activity_hashes" not in s: s["activity_hashes"] = {}
            return s
        except Exception:
            pass
    return {"chrome_hashes": {}, "activity_hashes": {}}

def atomic_save_state(state):
    try:
        fd, tmp = tempfile.mkstemp(dir="/tmp", prefix="state_", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, STATE_FILE)
    except Exception as e:
        print(f"[Medha-Core] ⚠️ Failed atomic write: {e}")

def delete_state():
    try:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
            print(f"[Medha-Core] 🧹 Deleted {STATE_FILE}")
    except Exception as e:
        print(f"[Medha-Core] ⚠️ Failed to delete state file: {e}")

state = load_state()

# ---------------- SIGNAL HANDLERS ----------------
@atexit.register
def on_exit():
    delete_state()
    print("[Medha-Core] Server exiting cleanly.")

def handle_signal(sig, frame):
    print(f"\n[Medha-Core] ⚠️ Signal {sig} received — cleaning up.")
    delete_state()
    os._exit(0)

for s in (signal.SIGINT, signal.SIGTERM, signal.SIGQUIT):
    try:
        signal.signal(s, handle_signal)
    except Exception:
        pass

# ---------------- UTILITIES ----------------
def read_json_lines(path):
    """Safely read JSONL file."""
    if not os.path.exists(path):
        return []
    data = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return data
    except Exception as e:
        print(f"[Medha-Core] ⚠️ Error reading {path}: {e}")
        return []

def canonical_json(obj):
    """Deterministic JSON for hashing."""
    try:
        return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    except Exception:
        return str(obj).encode("utf-8")

def entry_hash(entry):
    h = hashlib.sha256()
    h.update(canonical_json(entry))
    return h.hexdigest()

def entry_id(entry):
    """Stable identifier for entry."""
    try:
        if "tab_url" in entry and "_start_ts" in entry:
            return f"url::{entry['tab_url']}::{int(entry['_start_ts'])}"
        evt = entry.get("event")
        ts = int(entry.get("timestamp", 0))
        if evt:
            return f"evt::{evt}::{ts}"
        if ts:
            return f"ts::{ts}"
        return "gen::" + entry_hash(entry)[:12]
    except Exception:
        return "gen::" + entry_hash(entry)[:12]

# ---------------- INCREMENTAL COMPARISON ----------------
def read_incremental_by_hash(log_file, label, hash_key):
    """Compare current log with saved hashes, ignoring trivial fields."""
    separator = f"-----------------------{label.lower()} logs starting--------------------"
    entries = read_json_lines(log_file)
    if not entries:
        return f"{separator}\n[Log file empty or missing]"

    saved_map = state.get(hash_key, {})
    new_map = dict(saved_map)
    changed_entries = []

    volatile_fields = {"active_for", "last_update", "title_changed_at", "ended_at"}  # ignored
    for entry in entries:
        # Strip volatile fields before hashing
        stable_entry = {k: v for k, v in entry.items() if k not in volatile_fields}

        eid = entry_id(entry)
        h = entry_hash(stable_entry)
        prev_h = saved_map.get(eid)

        if prev_h != h:
            changed_entries.append(entry)

        new_map[eid] = h

    # Save new hash state
    state[hash_key] = new_map
    atomic_save_state(state)

    if not changed_entries:
        return f"{separator}\n[No new or changed log entries]"
    else:
        out = "\n".join(json.dumps(e, ensure_ascii=False) for e in changed_entries)
        return f"{separator}\n{out}"

# ---------------- ROUTES ----------------
@app.route('/healthcheck', methods=['GET'])
def health():
    print(f"[{time.strftime('%H:%M:%S')}] ✅ Health OK")
    return jsonify({"status": "connected", "message": "Log server running"}), 200

@app.route('/get_log_updates', methods=['GET'])
def get_updates():
    print(f"\n[{time.strftime('%H:%M:%S')}] 🔍 Log update request")

    chrome_out = read_incremental_by_hash(CHROME_LOG_PATH, "Chrome", "chrome_hashes")
    system_out = read_incremental_by_hash(ACTIVITY_LOG_PATH, "System", "activity_hashes")

    report = f"{chrome_out}\n\n{system_out}"
    print(f"✅ Sent {len(report)} chars of meaningful log updates")
    return jsonify({"status": "report_ready", "output": report.strip()})

# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("--- Starting Medha-Core Server (V6.7 - Meaningful Change Incremental) ---")
    print(f"🚀 Listening on http://127.0.0.1:{SERVER_PORT}")
    try:
        app.run(host="127.0.0.1", port=SERVER_PORT)
    finally:
        delete_state()
