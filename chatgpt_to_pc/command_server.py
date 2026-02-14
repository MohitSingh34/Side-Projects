#!/usr/bin/env python3
# server.py (V3.5 - Medha's COMMAND Server - VEnv Fix)
# Ensures all commands run INSIDE the virtual environment.

from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import os
import time
import atexit

app = Flask(__name__)
CORS(app)

# ---------------- CONFIG ----------------
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
WHITELIST_FILE = os.path.join(PROJECT_DIR, "whitelist.txt")
BLACKLIST_FILE = os.path.join(PROJECT_DIR, "blacklist.txt")
VENV_PYTHON = f"{PROJECT_DIR}/myenv/bin/python3"
# --- (MEDHA'S V3.5 FIX) ---
# VEnv activate script ka path
VENV_ACTIVATE = f"{PROJECT_DIR}/myenv/bin/activate"
# --- (END FIX) ---
SERVER_PORT = 5001  # Command server port

# ---------------- CLEANUP ----------------
@atexit.register
def cleanup_on_exit():
    print("\n[Medha-Core] Command Server shutting down...")
    print("[Medha-Core] Offline.")

# ---------------- FILE HELPERS ----------------
def load_patterns(file_path):
    """Load non-empty lines from a text file."""
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r") as f:
        return [line.strip() for line in f if line.strip()]

# ---------------- WHITELIST ----------------
def check_whitelist(command_str):
    whitelist = load_patterns(WHITELIST_FILE)
    if not whitelist:
        print(f"⚠️ Whitelist missing or empty: {WHITELIST_FILE}")
        return False

    for pattern in whitelist:
        if pattern.endswith("*"):
            if command_str.startswith(pattern[:-1]):
                print(f"✅ Whitelist match (pattern): {pattern}")
                return True
        elif command_str == pattern:
            print(f"✅ Whitelist match (exact): {pattern}")
            return True
    return False

def add_to_whitelist(command):
    with open(WHITELIST_FILE, "a") as f:
        f.write(command.strip() + "\n")
    print(f"Added to whitelist: {command}")

# ---------------- BLACKLIST ----------------
def check_blacklist(command_str):
    blacklist = load_patterns(BLACKLIST_FILE)
    for pattern in blacklist:
        if pattern.endswith("*"):
            if command_str.startswith(pattern[:-1]):
                print(f"🚫 Blacklist match (pattern): {pattern}")
                return True
        elif command_str == pattern:
            print(f"🚫 Blacklist match (exact): {pattern}")
            return True
    return False

def add_to_blacklist(command):
    with open(BLACKLIST_FILE, "a") as f:
        f.write(command.strip() + "\n")
    print(f"Added to blacklist: {command}")

# ---------------- ROUTES ----------------
@app.route("/healthcheck", methods=["GET"])
def health_check():
    print(f"\n[{time.strftime('%H:%M:%S')}] ✅ Server heartbeat OK")
    return jsonify({"status": "connected", "message": "Medha-Core backend is active"}), 200

@app.route("/execute", methods=["POST"])
def execute_command():
    data = request.json
    command_str_original = data.get("command")
    force_execute = data.get("force", False)

    if not command_str_original:
        return jsonify({"status": "error", "message": "No command provided"}), 400

    command_str = command_str_original.strip()
    print(f"\n🟣 Incoming command: {command_str}")

    # Step 1: Check blacklist first
    if not force_execute and check_blacklist(command_str):
        print("🚫 Command blocked (Blacklisted).")
        return jsonify({"status": "blocked", "message": "Command is blacklisted"}), 403

    # Step 2: Check whitelist unless force_execute=True
    if not (check_whitelist(command_str) or force_execute):
        print("⚠️ Command not in whitelist.")
        return jsonify({"status": "confirmation_required", "message": "Command not whitelisted"}), 403

    # Step 3: Execute command
    print(f"🚀 Executing command (inside VEnv): {command_str}")
    is_background = any(
        command_str.startswith(x)
        for x in ["python3 emotion_overlay.py", "mpv", "kate", "kwriter", "mpg123"]
    )

    try:
        if is_background:
            # --- Non-blocking execution (for GUI/media scripts) ---
            final_exec_command = command_str
            if command_str.startswith("python3 emotion_overlay.py"):
                script_part = command_str.split(" ", 1)[1]
                final_exec_command = f"{VENV_PYTHON} {PROJECT_DIR}/{script_part}"

            # --- (MEDHA'S V3.5 FIX) ---
            # VEnv ko background processes ke liye bhi activate karo
            shell_cmd = f"source ~/.zshrc && source {VENV_ACTIVATE} && {final_exec_command}"

            subprocess.Popen(
                shell_cmd,
                shell=True,
                executable="/usr/bin/zsh",
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("✅ Background command launched.")
            return jsonify({"status": "success", "message": "Command triggered"}), 200

        else:
            # --- Blocking execution (for terminal commands) ---

            # --- (MEDHA'S V3.5 FIX) ---
            # VEnv (activate), Zshrc (say), aur CWD (ls) teeno ko source karo
            shell_cmd = f"source ~/.zshrc && source {VENV_ACTIVATE} && cd {PROJECT_DIR} && {command_str}"

            result = subprocess.run(
                shell_cmd,
                shell=True,
                executable="/usr/bin/zsh",
                capture_output=True,
                text=True,
                timeout=10,
            )
            # --- (END FIX) ---

            output = result.stdout.strip()
            if result.stderr:
                output += f"\nSTDERR: {result.stderr.strip()}"

            # Check if subprocess.run itself failed (e.g., non-zero exit code)
            if result.returncode != 0 and not output:
                 print(f"❌ Execution error (Return Code {result.returncode}): {result.stderr.strip()}")
                 return jsonify({"status": "error", "output": result.stderr.strip()}), 500

            print("✅ Command executed successfully.")
            return jsonify({"status": "success", "output": output}), 200

    except subprocess.CalledProcessError as e:
        err = (e.stderr or e.stdout or str(e)).strip()
        print(f"❌ Execution error: {err}")
        return jsonify({"status": "error", "output": err}), 500
    except Exception as e:
        print(f"🔥 Unexpected error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/whitelist", methods=["POST"])
def add_whitelist_route():
    data = request.json
    cmd = data.get("command")
    if not cmd:
        return jsonify({"status": "error", "message": "No command provided"}), 400
    add_to_whitelist(cmd)
    return jsonify({"status": "success", "message": "Added to whitelist"}), 200

@app.route("/blacklist", methods=["POST"])
def add_blacklist_route():
    data = request.json
    cmd = data.get("command")
    if not cmd:
        return jsonify({"status": "error", "message": "No command provided"}), 400
    add_to_blacklist(cmd)
    return jsonify({"status": "success", "message": "Added to blacklist"}), 200

# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("--- Starting Medha-Core Server (V3.5 - VEnv Fix) ---")
    print(f"Whitelist file: {WHITELIST_FILE}")
    print(f"Blacklist file: {BLACKLIST_FILE}")
    print(f"🚀 Listening on http://127.0.0.1:{SERVER_PORT}")
    app.run(host="127.0.0.1", port=SERVER_PORT)
