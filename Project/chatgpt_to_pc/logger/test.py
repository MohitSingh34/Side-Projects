#!/usr/bin/env python3
# test_log_server.py — Fake Log Generator for ChatGPT Script Testing
# ⚙️ Port: 5003
# Generates fake Chrome + System logs to test Tampermonkey scripts.

from flask import Flask, jsonify
from flask_cors import CORS
import time, random, json

app = Flask(__name__)
CORS(app)

PORT = 5003

FAKE_DOMAINS = [
    "chat.openai.com", "mail.google.com", "youtube.com",
    "github.com", "reddit.com", "stackoverflow.com"
]

def fake_chrome_log():
    """Simulated Chrome log entry."""
    domain = random.choice(FAKE_DOMAINS)
    return {
        "timestamp": time.time(),
        "datetime": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "tab_title": f"Testing {domain} tab",
        "tab_url": f"https://{domain}/test",
        "tab_domain": domain,
        "event_type": random.choice([
            "new_tab_opened",
            "tab_switch_domain",
            "link_navigation",
            "title_update"
        ]),
        "user_activity_state": random.choice([
            "user_currently_active__on_this_link_or_tab",
            "user_not_active_on_this_link_or_tab"
        ])
    }

def fake_system_log():
    """Simulated system log entry."""
    return {
        "timestamp": time.time(),
        "datetime": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "window_name": random.choice([
            "VSCode", "Terminal", "Firefox", "Chrome", "Kate"
        ]),
        "event_type": random.choice(["window_opened", "window_switch"]),
        "user_activity_state": random.choice([
            "user_currently_active__on_this_app",
            "user_not_active_on_this_app"
        ])
    }

@app.route("/healthcheck", methods=["GET"])
def health():
    return jsonify({"status": "connected", "message": "Fake Log Server running (5003)"}), 200

@app.route("/get_log_updates", methods=["GET"])
def get_log_updates():
    chrome_logs = [fake_chrome_log() for _ in range(random.randint(1, 2))]
    system_logs = [fake_system_log() for _ in range(random.randint(1, 2))]

    output = (
        "-----------------------chrome logs starting now--------------------\n" +
        "\n".join(json.dumps(e, ensure_ascii=False) for e in chrome_logs) +
        "\n\n-----------------------system logs starting now--------------------\n" +
        "\n".join(json.dumps(e, ensure_ascii=False) for e in system_logs)
    )

    print(f"✅ Sent {len(chrome_logs)} Chrome + {len(system_logs)} System logs.")
    return jsonify({"status": "report_ready", "output": output.strip()})

if __name__ == "__main__":
    print(f"🚀 Fake Log Server running on http://127.0.0.1:{PORT}")
    app.run(host="127.0.0.1", port=PORT)
