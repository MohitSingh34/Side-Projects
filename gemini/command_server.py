#!/usr/bin/env python3
"""
Command server optimized for Mayra chat integration.
- Provides /healthcheck and /execute endpoints.
- /execute expects JSON: {"command": "...", "force": false}
- Returns JSON always with keys: status, output (string), message
- Uses whitelist/blacklist files placed next to this script.
- By default runs on 127.0.0.1:5001
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import os
import time
import atexit
from pathlib import Path

app = Flask(__name__)
CORS(app)

# CONFIG
PROJECT_DIR = Path(__file__).parent.resolve()
WHITELIST_FILE = PROJECT_DIR / "whitelist.txt"
BLACKLIST_FILE = PROJECT_DIR / "blacklist.txt"
VENV_PYTHON = PROJECT_DIR / "myenv/bin/python3"
VENV_ACTIVATE = PROJECT_DIR / "myenv/bin/activate"
SERVER_PORT = 5001

# cleanup
@atexit.register
def cleanup_on_exit():
    print("\n[CommandServer] Shutting down...")

# utils
def load_patterns(path: Path):
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def check_blacklist(cmd: str):
    for pat in load_patterns(BLACKLIST_FILE):
        if pat.endswith("*"):
            if cmd.startswith(pat[:-1]):
                return True
        elif cmd == pat:
            return True
    return False

def check_whitelist(cmd: str):
    wl = load_patterns(WHITELIST_FILE)
    if not wl:
        return False
    for pat in wl:
        if pat.endswith("*"):
            if cmd.startswith(pat[:-1]):
                return True
        elif cmd == pat:
            return True
    return False

def add_to_file(path: Path, cmd: str):
    with path.open("a", encoding="utf-8") as f:
        f.write(cmd.strip() + "\n")

# endpoints
@app.route("/healthcheck", methods=["GET"])
def healthcheck():
    return jsonify({"status": "ok", "message": "Command server alive"}), 200

@app.route("/execute", methods=["POST"])
def execute():
    data = request.json or {}
    cmd = data.get("command")
    force = bool(data.get("force", False))
    if not cmd:
        return jsonify({"status": "error", "output": "", "message": "No command provided"}), 400

    cmd = str(cmd).strip()
    print(f"[{time.strftime('%H:%M:%S')}] Incoming command: {cmd}")

    # blacklist check first
    if not force and check_blacklist(cmd):
        return jsonify({"status": "blocked", "output": "", "message": "Command blacklisted"}), 403

    # whitelist unless forced
    if not force and not check_whitelist(cmd):
        return jsonify({"status": "confirmation_required", "output": "", "message": "Command not whitelisted"}), 403

    # decide if background
    background_prefixes = ("python3 emotion_overlay.py", "mpv", "kate", "kwriter", "mpg123")
    is_background = any(cmd.startswith(p) for p in background_prefixes)

    try:
        if is_background:
            # For known background commands, run non-blocking
            final_cmd = cmd
            if cmd.startswith("python3 emotion_overlay.py"):
                # convert to venv python + path
                final_cmd = f"{VENV_PYTHON} {PROJECT_DIR}/{cmd.split(' ', 1)[1]}"
            shell_cmd = f"source ~/.zshrc && source {VENV_ACTIVATE} && {final_cmd}"
            subprocess.Popen(shell_cmd, shell=True, executable="/usr/bin/zsh",
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return jsonify({"status": "success", "output": "", "message": "Background command launched"}), 200
        else:
            # blocking execution, safe timeout
            shell_cmd = f"source ~/.zshrc && source {VENV_ACTIVATE} && cd {PROJECT_DIR} && {cmd}"
            result = subprocess.run(shell_cmd, shell=True, executable="/usr/bin/zsh",
                                     capture_output=True, text=True, timeout=15)
            output = (result.stdout or "").strip()
            if result.stderr:
                output += ("\nSTDERR: " + result.stderr.strip()) if output else ("STDERR: " + result.stderr.strip())
            if result.returncode != 0 and not output:
                return jsonify({"status": "error", "output": "", "message": f"Command failed (code {result.returncode})"}), 500
            return jsonify({"status": "success", "output": output, "message": "Command executed"}), 200
    except subprocess.TimeoutExpired as te:
        return jsonify({"status": "error", "output": "", "message": f"Timeout: {te}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "output": "", "message": str(e)}), 500

@app.route("/whitelist", methods=["POST"])
def add_whitelist():
    data = request.json or {}
    cmd = data.get("command")
    if not cmd:
        return jsonify({"status": "error", "message": "No command provided"}), 400
    add_to_file(WHITELIST_FILE, cmd)
    return jsonify({"status": "success", "message": "Added to whitelist"}), 200

@app.route("/blacklist", methods=["POST"])
def add_blacklist():
    data = request.json or {}
    cmd = data.get("command")
    if not cmd:
        return jsonify({"status": "error", "message": "No command provided"}), 400
    add_to_file(BLACKLIST_FILE, cmd)
    return jsonify({"status": "success", "message": "Added to blacklist"}), 200

if __name__ == "__main__":
    print(f"Starting Command Server on http://127.0.0.1:{SERVER_PORT}")
    app.run(host="127.0.0.1", port=SERVER_PORT)
