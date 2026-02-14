#!/usr/bin/env python3
# Chrome Domain Activity Logger v6.0
# - Uses domain as base identity
# - Auto-updates entries of same domain (url, title, duration, etc.)
# - Writes new entry only when domain changes
# - Keeps user_activity_state for current active tab

import os, time, json, requests, psutil, datetime, tempfile
from urllib.parse import urlparse

LOG_FILE = "/tmp/chrome_activity_log.json"
STATE_FILE = "/tmp/chrome_logger_state.json"
BROWSER_PROCESSES = ["chrome", "brave", "chromium"]
PORT = 9222
CHECK_INTERVAL = 3
MAX_ENTRIES = 300

ACTIVE_STR = "user_currently_active__on_this_link_or_tab"
NOT_ACTIVE_STR = "user_not_active_on_this_link_or_tab"

# ------------------ UTILITIES ------------------
def now(): return time.time()
def iso_now(): return datetime.datetime.now().isoformat(timespec="seconds")

def atomic_write(path, entries):
    try:
        fd, tmp = tempfile.mkstemp(dir="/tmp", prefix="chrome_log_", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        os.replace(tmp, path)
    except Exception as e:
        print(f"[chrome-logger] Write error: {e}")

def is_chrome_running():
    for proc in psutil.process_iter(attrs=["name", "cmdline"]):
        name = (proc.info.get("name") or "").lower()
        if any(b in name for b in BROWSER_PROCESSES):
            try:
                cmd = " ".join(proc.info.get("cmdline") or [])
            except Exception:
                cmd = ""
            if "--type=" in cmd and "--type=browser" not in cmd:
                continue
            return True
    return False

# ------------------ FETCH TAB INFO ------------------
def fetch_tabs():
    try:
        res = requests.get(f"http://127.0.0.1:{PORT}/json", timeout=2)
        return res.json()
    except Exception:
        return []

def extract_info(tab):
    url = tab.get("url", "")
    parsed = urlparse(url) if url.startswith("http") else None
    domain = parsed.netloc if parsed else ""
    title = tab.get("title", "Unknown Tab")[:120]
    return url, domain, title

def is_noisy_tab(tab):
    url = tab.get("url", "") or ""
    ttype = tab.get("type", "")
    title = tab.get("title", "") or ""
    NOISY_TYPES = ["service_worker", "background_page", "iframe", "extension"]
    NOISY_PATTERNS = ["chrome-extension://", "accounts.google.com/RotateCookiesPage"]
    if ttype in NOISY_TYPES: return True
    if any(p in url for p in NOISY_PATTERNS): return True
    if not title or "Service Worker" in title: return True
    return False

def get_active_tab():
    tabs = [t for t in fetch_tabs() if not is_noisy_tab(t)]
    if not tabs:
        return None
    for t in tabs:
        desc = (t.get("description") or "").lower()
        if "active" in desc:
            return t
    return tabs[0]

# ------------------ LOGGER CLASS ------------------
class DomainLogger:
    def __init__(self):
        self.logs = self.load_logs()
        self.active_domains = {}
        if self.logs:
            for e in self.logs:
                domain = e.get("tab_domain")
                if domain:
                    self.active_domains[domain] = e
        print("[chrome-logger] Ready — domain-based tracking started.")

    def load_logs(self):
        if not os.path.exists(LOG_FILE):
            return []
        try:
            with open(LOG_FILE, "r") as f:
                return [json.loads(l) for l in f if l.strip()]
        except Exception:
            return []

    def write_logs(self, active_domain=None):
        out = []
        for e in self.logs[-MAX_ENTRIES:]:
            if e.get("tab_domain") == active_domain:
                e["user_activity_state"] = ACTIVE_STR
            else:
                e["user_activity_state"] = NOT_ACTIVE_STR
            out.append(e)
        atomic_write(LOG_FILE, out)

    def update_or_create(self, url, domain, title, active_domain):
        now_t = now()
        if domain in self.active_domains:
            e = self.active_domains[domain]
            e["tab_url"] = url
            e["url"] = url
            e["tab_title"] = title
            e["active_for"] = round(now_t - e["_start_ts"], 1)
            e["last_update"] = iso_now()
            e["event_type"] = "domain_continued"
            print(f"[chrome-logger] 🔄 Updated {domain} (active {e['active_for']}s)")
        else:
            e = {
                "timestamp": now_t,
                "datetime": iso_now(),
                "tab_title": title,
                "tab_url": url,
                "url": url,
                "tab_domain": domain,
                "_start_ts": now_t,
                "active_for": 0.0,
                "event_type": "new_domain_opened"
            }
            self.logs.append(e)
            self.active_domains[domain] = e
            print(f"[chrome-logger] 🆕 New domain tracked: {domain}")

        self.write_logs(active_domain=active_domain)

# ------------------ MAIN LOOP ------------------
def main():
    print("=" * 60)
    print("🌐 Chrome Domain Activity Logger v6.0 — domain-based incremental tracking")
    print(f"💾 Log file: {LOG_FILE}")
    print("=" * 60)

    tracker = None
    chrome_running = False

    try:
        while True:
            running = is_chrome_running()
            if running and not chrome_running:
                tracker = DomainLogger()
                chrome_running = True

            elif not running and chrome_running:
                print("[chrome-logger] 🔴 Chrome closed — stopping tracking.")
                tracker = None
                chrome_running = False
                time.sleep(3)
                continue

            if running and tracker:
                active_tab = get_active_tab()
                if not active_tab:
                    time.sleep(CHECK_INTERVAL)
                    continue

                url, domain, title = extract_info(active_tab)
                if not domain:
                    time.sleep(CHECK_INTERVAL)
                    continue

                tracker.update_or_create(url, domain, title, active_domain=domain)

            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
