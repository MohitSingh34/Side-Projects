#!/usr/bin/env python3
# log_server.py (V7.0 - Enhanced Activity Logger Support)
# Supports new activity logger format with cumulative timing and WM_CLASS deduplication
# Sends only entries that meaningfully changed since last request.

from flask import Flask, jsonify
from flask_cors import CORS
import os, json, time, atexit, signal, hashlib, tempfile

app = Flask(__name__)
CORS(app)

SERVER_PORT = 5002
CHROME_LOG_PATH = "/tmp/chrome_activity_log.json"
ACTIVITY_LOG_PATH = "/tmp/activity_log.json"  # Updated activity logger file
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
        with os.fdopen(fd, "w", encoding="ascii") as f:
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
    """Stable identifier for entry - enhanced for activity logger."""
    try:
        # For activity logger entries
        if "_id" in entry:
            return f"activity::{entry['_id']}"

        # For Chrome logger entries
        if "tab_url" in entry and "_start_ts" in entry:
            return f"chrome_url::{entry['tab_url']}::{int(entry['_start_ts'])}"

        # For system events
        evt = entry.get("event")
        ts = int(entry.get("timestamp", 0))
        if evt:
            return f"system_evt::{evt}::{ts}"

        # For WM_CLASS based entries
        wm_class = entry.get("wm_class_clean") or entry.get("wm_class")
        if wm_class:
            return f"wm_class::{wm_class}::{ts}"

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

    # Enhanced volatile fields for activity logger
    volatile_fields = {
        "active_for", "last_update", "title_changed_at", "ended_at",
        "cumulative_active_for", "last_session_for", "last_update",
        "user_activity_state"  # This changes frequently but is meaningful
    }

    for entry in entries:
        # Create stable version by removing volatile fields
        stable_entry = {k: v for k, v in entry.items() if k not in volatile_fields}

        eid = entry_id(entry)
        h = entry_hash(stable_entry)
        prev_h = saved_map.get(eid)

        if prev_h != h:
            # This is a meaningful change - include the full entry
            changed_entries.append(entry)
            print(f"[Medha-Core] 🔍 {label} change detected: {eid}")

        new_map[eid] = h

    # Save new hash state
    state[hash_key] = new_map
    atomic_save_state(state)

    if not changed_entries:
        return f"{separator}\n[No new or changed log entries]"
    else:
        # Format entries for better readability
        formatted_entries = []
        for entry in changed_entries:
            try:
                # Enhanced formatting for activity logger
                if "_id" in entry:  # Activity logger entry
                    app_name = entry.get("wm_class_clean", "unknown")
                    window_name = entry.get("window_name", "unknown")
                    event_type = entry.get("event_type", "unknown")
                    cumulative_time = entry.get("cumulative_active_for", 0)
                    current_session = entry.get("active_for", 0)

                    formatted = f"📱 {app_name} | {window_name} | {event_type}"
                    if cumulative_time > 0:
                        formatted += f" | Total: {cumulative_time}s"
                    if current_session > 0:
                        formatted += f" | Current: {current_session}s"
                    if "user_activity_state" in entry:
                        status = "🟢 ACTIVE" if entry["user_activity_state"] == "user_currently_active__on_this_app" else "⚪ INACTIVE"
                        formatted += f" | {status}"

                    formatted_entries.append(formatted)

                # Chrome logger entries (keep existing format)
                elif "tab_url" in entry:
                    url = entry.get("tab_url", "unknown")
                    title = entry.get("tab_title", "unknown")
                    duration = entry.get("active_for", 0)
                    formatted_entries.append(f"🌐 {title} | {url} | {duration}s")

                # System events
                elif "event" in entry:
                    event = entry.get("event", "unknown")
                    message = entry.get("message", "")
                    formatted_entries.append(f"⚡ {event} | {message}")

                else:
                    # Fallback to JSON
                    formatted_entries.append(json.dumps(entry, ensure_ascii=False))

            except Exception as e:
                formatted_entries.append(f"[Format error: {e}]")

        out = "\n".join(formatted_entries)
        return f"{separator}\n{out}"

# ---------------- ENHANCED ACTIVITY ANALYSIS ----------------
def analyze_activity_trends(activity_entries):
    """Provide summary of current activity state."""
    if not activity_entries:
        return "No activity data available"

    current_active = None
    app_usage = {}

    for entry in activity_entries[-20:]:  # Last 20 entries for trend analysis
        wm_class = entry.get("wm_class_clean")
        if not wm_class:
            continue

        # Track current active window
        if entry.get("user_activity_state") == "user_currently_active__on_this_app":
            current_active = {
                "app": wm_class,
                "window": entry.get("window_name", "unknown"),
                "session_time": entry.get("active_for", 0),
                "total_time": entry.get("cumulative_active_for", 0)
            }

        # Track cumulative usage
        if wm_class not in app_usage:
            app_usage[wm_class] = 0
        app_usage[wm_class] += entry.get("cumulative_active_for", 0)

    # Build summary
    summary_parts = []

    if current_active:
        summary_parts.append(f"👤 CURRENTLY ACTIVE: {current_active['app']}")
        summary_parts.append(f"   Window: {current_active['window']}")
        summary_parts.append(f"   Session: {current_active['session_time']}s | Total: {current_active['total_time']}s")

    # Top used apps
    if app_usage:
        top_apps = sorted(app_usage.items(), key=lambda x: x[1], reverse=True)[:3]
        summary_parts.append("🏆 TOP APPS:")
        for app, total_time in top_apps:
            summary_parts.append(f"   {app}: {total_time}s")

    return "\n".join(summary_parts) if summary_parts else "No significant activity trends"

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

    # Enhanced activity analysis
    activity_entries = read_json_lines(ACTIVITY_LOG_PATH)
    activity_summary = analyze_activity_trends(activity_entries)

    report = f"{chrome_out}\n\n{system_out}\n\n📊 ACTIVITY SUMMARY:\n{activity_summary}"
    print(f"✅ Sent meaningful log updates with activity analysis")
    return jsonify({"status": "report_ready", "output": report.strip()})

@app.route('/get_activity_summary', methods=['GET'])
def get_activity_summary():
    """Enhanced endpoint for activity-specific data"""
    activity_entries = read_json_lines(ACTIVITY_LOG_PATH)
    summary = analyze_activity_trends(activity_entries)

    return jsonify({
        "status": "success",
        "summary": summary,
        "total_entries": len(activity_entries)
    })

# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("--- Starting Medha-Core Server (V7.0 - Enhanced Activity Logger) ---")
    print(f"🚀 Listening on http://127.0.0.1:{SERVER_PORT}")
    print(f"📊 Activity logger: {ACTIVITY_LOG_PATH}")
    print(f"🌐 Chrome logger: {CHROME_LOG_PATH}")
    try:
        app.run(host="127.0.0.1", port=SERVER_PORT)
    finally:
        delete_state()
