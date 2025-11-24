#!/usr/bin/env python3
# server.py (V3.2 - Medha's COMMAND Server - Absolute Path Fix)
from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import shlex
import os
import atexit
import time

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
# --- (MEDHA'S V3.2 FIX) ---
# Whitelist ka poora path use karo
WHITELIST_FILE = os.path.join(PROJECT_DIR, "whitelist.txt")
# --- (END FIX) ---
VENV_PYTHON = f"{PROJECT_DIR}/myenv/bin/python3"
SERVER_PORT = 5001

@atexit.register
def cleanup_on_exit():
    print("\n[Medha-Core] Command Server shutting down...")
    print("[Medha-Core] Offline.")

# --- Whitelist Logic (Same as before) ---
def check_whitelist(command_str):
    if not os.path.exists(WHITELIST_FILE):
        # (FIX) Print error agar file nahi mili
        print(f"❌ CRITICAL ERROR: Whitelist file not found at {WHITELIST_FILE}")
        return False
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
    # (FIX) Absolute path use karo
    with open(WHITELIST_FILE, "a") as f:
        f.write(command + "\n")

# --- Endpoints ---
@app.route('/healthcheck', methods=['GET'])
def health_check():
    print(f"\n[{time.strftime('%H:%M:%S')}] ✅ Command server (V3.2) connection check successful.")
    return jsonify({"status": "connected", "message": "Command Backend is active"}), 200

@app.route('/execute', methods=['POST'])
def execute_command():
    # (No Change - V3.1 Logic)
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
    is_background_command = False
    if (command_str.startswith("python3 emotion_overlay.py") or
        command_str.startswith("mpv") or
        command_str.startswith("kate") or
        command_str.startswith("kwriter") or
        command_str.startswith("mpg123")):
        is_background_command = True
    if is_background_command:
        try:
            final_exec_command = command_str
            if command_str.startswith("python3 emotion_overlay.py"):
                script_part = command_str.split(" ", 1)[1]
                final_exec_command = f'{VENV_PYTHON} {PROJECT_DIR}/{script_part}'
            subprocess.Popen(f'source ~/.zshrc && {final_exec_command}', shell=True, executable="/usr/bin/zsh", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return jsonify({'status': 'success', 'message': f'Command ({command_str[:20]}...) triggered.'}), 200
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
    data = request.json
    command_str = data.get('command')
    if not command_str:
        return jsonify({"status": "error", "message": "No command provided"}), 400
    add_to_whitelist(command_str) # Yeh ab absolute path use karega
    print(f"Added to whitelist (Exact): {command_str}")
    return jsonify({"status": "success", "message": "Command added to whitelist"}), 200

if __name__ == '__main__':
    print("--- Starting Medha-Core Server (V3.2 - Absolute Path Fix) ---")
    print(f"Whitelist file located at: {WHITELIST_FILE}")
    print(f"🚀 Listening on http://127.0.0.1:{SERVER_PORT}")
    app.run(host='127.0.0.1', port=SERVER_PORT)
