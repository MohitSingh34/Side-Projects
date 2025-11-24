#!/usr/bin/env python3
# server.py (V2.6 - Medha's Autonomous Enhanced Formatting)
# Logic based on Mohit's 'RawJSONMonitor' (Signature Set)
from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import shlex
import os
import json
import time
import atexit

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
WHITELIST_FILE = "whitelist.txt"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = f"{PROJECT_DIR}/myenv/bin/python3"

# --- LOG FILES ---
CHROME_LOG_PATH = "/tmp/chrome_activity_log.json"
ACTIVITY_LOG_PATH = "/tmp/activity_log.json"

# --- In-Memory State for Log Tailing (Aapka 'temp1') ---
STATE = {
    "chrome_signatures": set(),
    "activity_signatures": set(),
    "is_first_run": True # Pehli baar full logs load karne ke liye
}

@atexit.register
def cleanup_on_exit():
    """Server band hone par 'first run' flag ko reset karta hai (agar zaroorat ho)"""
    print("\n[Medha-Core] Server shutting down...")
    print("[Medha-Core] Autonomous state will reset on next launch.")
    print("[Medha-Core] Offline.")

# --- Whitelist Logic (No Change) ---
def check_whitelist(command_str):
    if not os.path.exists(WHITELIST_FILE): return False
    with open(WHITELIST_FILE, "r") as f:
        for pattern in f:
            pattern = pattern.strip()
            if not pattern: continue
            if pattern.endswith('*'):
                base_pattern = pattern[:-1]
                if command_str.startswith(base_pattern):
                    print(f"Whitelist match (Pattern): '{pattern}' -> '{command_str}'")
                    return True
            if command_str == pattern:
                print(f"Whitelist match (Exact): '{command_str}'")
                return True
    return False

def add_to_whitelist(command):
    with open(WHITELIST_FILE, "a") as f:
        f.write(command + "\n")

# --- Log Tailing Logic (Signature-based - No Change) ---

def get_entry_signature(entry):
    if isinstance(entry, dict):
        if 'tab_id' in entry: # Chrome Log
            return f"{entry.get('timestamp', '')}_{entry.get('tab_id', '')}_{entry.get('tab_title', '')}"
        if 'window_name' in entry: # Activity Log
            return f"{entry.get('timestamp', '')}_{entry.get('window_name', '')}"
    return str(entry)

def get_log_content_by_signature(log_file_path, state_key):
    global STATE
    raw_lines = []
    try:
        if not os.path.exists(log_file_path):
            return ("", set())
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            raw_lines = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"❌ Error reading {log_file_path}: {e}")
        return ("", set())

    current_signatures = set()
    line_to_signature_map = {}
    for line in raw_lines:
        try:
            entry = json.loads(line)
            sig = get_entry_signature(entry)
            current_signatures.add(sig)
            line_to_signature_map[sig] = line
        except json.JSONDecodeError:
            continue

    if STATE["is_first_run"]:
        STATE[state_key] = current_signatures
        print(f"🧠 [Medha-Core] Baseline set for {log_file_path}. Sending full file ({len(raw_lines)} lines).")
        return ("\n".join(raw_lines), current_signatures)
    else:
        new_signatures = current_signatures - STATE[state_key]
        new_raw_logs = []
        if new_signatures:
            for sig in new_signatures:
                if sig in line_to_signature_map:
                    new_raw_logs.append(line_to_signature_map[sig])
        STATE[state_key] = current_signatures
        return ("\n".join(new_raw_logs), current_signatures)

# --- Endpoints ---

@app.route('/healthcheck', methods=['GET'])
def health_check():
    print("\n✅ SUCCESS: Medha-Core (V2.6) connected to frontend.\n")
    return jsonify({"status": "connected", "message": "Backend is active"}), 200

@app.route('/execute', methods=['POST'])
def execute_command():
    # (No Change - V1.6 Logic)
    data = request.json
    command_str_original = data.get('command')
    force_execute = data.get('force', False)
    if not command_str_original:
        return jsonify({"status": "error", "message": "No command provided"}), 400
    command_str = command_str_original.strip()
    print(f"\nReceived raw command: {command_str}")
    if not (check_whitelist(command_str) or force_execute):
        print(f"Command not in whitelist: {command_str}")
        return jsonify({"status": "confirmation_required", "message": "Command not whitelisted"}), 403
    print(f"Executing command: {command_str}")
    if command_str.startswith("python3 emotion_overlay.py"): # Legacy support
        try:
            script_part = command_str.split(" ", 1)[1]
            final_exec_command = f'{VENV_PYTHON} {PROJECT_DIR}/{script_part}'
            subprocess.Popen(f'source ~/.zshrc && {final_exec_command}', shell=True, executable="/usr/bin/zsh", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return jsonify({'status': 'success', 'message': 'Emotion overlay triggered.'}), 200
        except Exception as e:
            return jsonify({'status': "error", 'message': str(e)}), 500
    else:
        try:
            full_shell_command = f'source ~/.zshrc && {command_str}'
            result = subprocess.run(
                full_shell_command, shell=True, executable="/usr/bin/zsh",
                capture_output=True, text=True, timeout=10, check=True
            )
            output = result.stdout.strip()
            if result.stderr: output += f"\nSTDERR: {result.stderr.strip()}"
            print(f"✅ Output captured. Sending to frontend.")
            return jsonify({'status': 'success', 'output': output})
        except subprocess.CalledProcessError as e:
            error_output = (e.stderr or e.stdout).strip()
            return jsonify({'status': 'error', 'output': error_output})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/whitelist', methods=['POST'])
def manage_whitelist():
    # (No Change)
    data = request.json
    command_str = data.get('command')
    if not command_str:
        return jsonify({"status": "error", "message": "No command provided"}), 400
    add_to_whitelist(command_str)
    print(f"Added to whitelist (Exact): {command_str}")
    return jsonify({"status": "success", "message": "Command added to whitelist"}), 200

# --- (MODIFIED) AUTONOMOUS ENDPOINT (V2.6 ENHANCED FORMATTING) ---
@app.route('/get_log_updates', methods=['GET'])
def get_log_updates():
    """
    Called by Tampermonkey every 1 minute.
    Fetches ONLY new content and formats it cleanly (as ONE string).
    """
    print(f"\n[{time.strftime('%H:%M:%S')}] 🧠 Autonomous log request received...")

    chrome_updates_str, _ = get_log_content_by_signature(CHROME_LOG_PATH, "chrome_signatures")
    activity_updates_str, _ = get_log_content_by_signature(ACTIVITY_LOG_PATH, "activity_signatures")

    if STATE["is_first_run"]:
        print("...Baseline populated. Sending full report.")
        STATE["is_first_run"] = False # Baseline set ho gaya
        # Pehli run par bhi "No new activity" messages aa sakte hain agar file empty hai

    elif not chrome_updates_str and not activity_updates_str:
        print("...No new log activity.")
        # Agar first run nahi hai aur koi update nahi hai, toh yeh message bhejo
        return jsonify({"status": "report_ready", "output": "No new activity detected in system/chrome"})

    # --- (NEW FORMATTING LOGIC V2.6 - MEDHA'S FIX) ---

    # 1. Check Chrome logs
    if not chrome_updates_str:
        formatted_chrome_logs = "No new activity in chrome"
    else:
        # Don't destroy newlines (User request)
        formatted_chrome_logs = chrome_updates_str

    # 2. Check System logs
    if not activity_updates_str:
        formatted_activity_logs = "No new activity in system"
    else:
        # Don't destroy newlines
        formatted_activity_logs = activity_updates_str

    # 3. Combine them using the requested multiline format (f-string)
    #    Yeh hamesha dono keys (chrome aur system) bhejega.
    report_message = f"""chrome logs:
{formatted_chrome_logs}

now system logs are starting :
{formatted_activity_logs}"""

    # --- (END NEW FORMATTING V2.6) ---

    print(f"✅ Sending {len(report_message)} chars of NEW log data to Medha.")
    return jsonify({"status": "report_ready", "output": report_message.strip()}) # .strip() to remove leading/trailing whitespace

if __name__ == '__main__':
    print("--- Starting Medha-Core Server (V2.6 - Enhanced Formatting) ---")
    print(f"Whitelist file located at: {os.path.abspath(WHITELIST_FILE)}")
    print("Waiting for frontend script to connect...")
    app.run(host='127.0.0.1', port=5000)
