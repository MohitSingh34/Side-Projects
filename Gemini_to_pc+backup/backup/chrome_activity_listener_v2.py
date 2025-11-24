#!/usr/bin/env python3
import os
import time
import json
import requests
import psutil
import datetime
import hashlib

LOG_FILE = "/tmp/chrome_activity_log.json"
BROWSER_PROCESSES = ["chrome", "brave", "chromium"]
PORT = 9222
MAX_ENTRIES = 100  # Maximum total lines in log file
CHECK_INTERVAL = 3

# Filter out noisy tabs
NOISY_TAB_TYPES = ["service_worker", "background_page", "iframe", "extension"]
NOISY_URL_PATTERNS = ["chrome-extension://", "googletagmanager.com", "accounts.google.com/RotateCookiesPage"]

class TabTracker:
    def __init__(self):
        self.current_tab = None
        self.tab_switch_count = 0

def is_browser_running():
    """Check if browser process is running"""
    for proc in psutil.process_iter(attrs=["name"]):
        if proc.info["name"] and any(b in proc.info["name"].lower() for b in BROWSER_PROCESSES):
            return True
    return False

def fetch_tabs():
    """Fetch all tabs from Chrome debug interface"""
    try:
        res = requests.get(f"http://127.0.0.1:{PORT}/json", timeout=2)
        return res.json()
    except:
        return []

def is_noisy_tab(tab):
    """Filter out system/extension tabs"""
    tab_type = tab.get("type", "")
    url = tab.get("url", "")
    title = tab.get("title", "")

    if tab_type in NOISY_TAB_TYPES:
        return True
    if any(pattern in url for pattern in NOISY_URL_PATTERNS):
        return True
    if not title or "Service Worker" in title:
        return True
    return False

def get_active_tab(tabs):
    """Find the currently active tab"""
    meaningful_tabs = [tab for tab in tabs if not is_noisy_tab(tab)]

    if not meaningful_tabs:
        return None

    for tab in meaningful_tabs:
        description = tab.get("description", "").lower()
        if "active" in description:
            return tab

    return meaningful_tabs[0] if meaningful_tabs else None

def get_tab_fingerprint(tab):
    """Create unique identifier for tab"""
    if not tab:
        return ""
    tab_data = f"{tab.get('title', '')}|{tab.get('url', '')}|{tab.get('type', '')}"
    return hashlib.md5(tab_data.encode()).hexdigest()

def format_tab_info(tab):
    """Format tab information for clean display"""
    title = tab.get('title', 'Unknown Tab')[:60]
    url = tab.get('url', '')[:80]

    # Extract domain
    domain = ""
    if url.startswith('http'):
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc

    return {"title": title, "url": url, "domain": domain}

def create_tab_entry(tab, is_new_tab=False):
    """Create a tab log entry"""
    tab_info = format_tab_info(tab)

    entry = {
        "timestamp": time.time(),
        "datetime": datetime.datetime.now().isoformat(),
        "time": datetime.datetime.now().strftime("%H:%M:%S"),
        "tab_title": tab_info["title"],
        "tab_url": tab_info["url"],
        "tab_domain": tab_info["domain"],
        "tab_id": get_tab_fingerprint(tab),
        "event_type": "tab_switch" if is_new_tab else "tab_active"
    }

    return entry

def load_logs():
    """Load existing logs from file"""
    if not os.path.exists(LOG_FILE):
        return []

    try:
        with open(LOG_FILE, "r") as f:
            logs = []
            for line in f:
                if line.strip():
                    try:
                        logs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            return logs
    except Exception:
        return []

def save_logs_optimized(logs):
    """Save logs to file with automatic cleanup of old entries"""
    # Remove oldest entries if we exceed MAX_ENTRIES
    if len(logs) > MAX_ENTRIES:
        # Keep only the most recent MAX_ENTRIES
        logs_to_remove = len(logs) - MAX_ENTRIES
        logs = logs[logs_to_remove:]
        print(f"🧹 Removed {logs_to_remove} old entries, keeping {len(logs)} most recent")

    try:
        # Write to temporary file first to prevent corruption
        temp_file = LOG_FILE + ".tmp"
        with open(temp_file, "w") as f:
            for entry in logs:
                f.write(json.dumps(entry) + "\n")
            f.flush()  # Force flush to disk
            os.fsync(f.fileno())  # Ensure data is written to disk

        # Atomically replace the original file
        os.replace(temp_file, LOG_FILE)

    except Exception as e:
        print(f"⚠️  Save error: {e}")

def print_tab_activity(tab, activity_type):
    """Print clean activity messages"""
    time_str = datetime.datetime.now().strftime("%H:%M:%S")
    tab_info = format_tab_info(tab)

    if activity_type == "new_tab":
        print(f"🆕 [{time_str}] Switched to: {tab_info['title']}")
        print(f"   🌐 {tab_info['domain']}")

def main():
    print("=" * 50)
    print("📑 Chrome Tab Tracker")
    print(f"💾 Log file: {LOG_FILE}")
    print(f"📊 Max entries: {MAX_ENTRIES}")
    print("=" * 50)

    tracker = TabTracker()
    logs = load_logs()
    current_tab_id = None

    # Show initial log count
    print(f"📁 Loaded {len(logs)} existing log entries")

    while True:
        if not is_browser_running():
            if os.path.exists(LOG_FILE):
                os.remove(LOG_FILE)
                logs = []
                print("⏹️  Browser closed - logs cleared")
            time.sleep(5)
            continue

        all_tabs = fetch_tabs()

        if all_tabs:
            meaningful_tabs = [tab for tab in all_tabs if not is_noisy_tab(tab)]
            active_tab = get_active_tab(meaningful_tabs)

            if active_tab:
                active_tab_id = get_tab_fingerprint(active_tab)

                # Check if this is a new tab
                if active_tab_id != current_tab_id:
                    # Create new tab entry
                    new_entry = create_tab_entry(active_tab, is_new_tab=True)
                    logs.append(new_entry)
                    current_tab_id = active_tab_id
                    tracker.tab_switch_count += 1

                    print_tab_activity(active_tab, "new_tab")
                    print(f"   🔢 Total tab switches: {tracker.tab_switch_count}")

                    # Save logs immediately on tab switch
                    save_logs_optimized(logs)
                    print(f"💾 Logs saved ({len(logs)} entries)")

                # Periodic save every 30 seconds if no tab switches
                elif int(time.time()) % 30 == 0:
                    # Create a heartbeat entry to show tab is still active
                    active_entry = create_tab_entry(active_tab, is_new_tab=False)
                    logs.append(active_entry)
                    save_logs_optimized(logs)
                    print(f"💓 [{datetime.datetime.now().strftime('%H:%M:%S')}] Tab still active: {format_tab_info(active_tab)['title'][:40]}...")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Tracker stopped by user")
        # Final save attempt
        try:
            from main import logs, save_logs_optimized
            save_logs_optimized(logs)
            print("💾 Final logs saved")
        except:
            pass
    except Exception as e:
        print(f"❌ Error: {e}")
