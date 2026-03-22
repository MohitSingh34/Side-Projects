# server.py (Corrected V1.3 - Output Capture Fix)
from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import shlex
import os

app = Flask(__name__)
CORS(app)

WHITELIST_FILE = "whitelist.txt"

# --- Smart Whitelist Checker (No Change) ---
def check_whitelist(command_str):
    if not os.path.exists(WHITELIST_FILE):
        return False
    with open(WHITELIST_FILE, "r") as f:
        for pattern in f:
            pattern = pattern.strip()
            if not pattern:
                continue
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

# --- Endpoints ---
@app.route('/healthcheck', methods=['GET'])
def health_check():
    print("\n✅ SUCCESS: Frontend script successfully connected to backend server!\n")
    return jsonify({"status": "connected", "message": "Backend is active"}), 200

# --- THIS IS THE CORRECTED FUNCTION ---
@app.route('/execute', methods=['POST'])
def execute_command():
    data = request.json
    command_str = data.get('command')
    force_execute = data.get('force', False)

    if not command_str:
        return jsonify({"status": "error", "message": "No command provided"}), 400

    command_str = command_str.strip()
    print(f"\nReceived raw command: {data.get('command')}")
    print(f"Final command to execute: {command_str}")

    # Whitelist check
    if check_whitelist(command_str) or force_execute:
        print(f"Executing command: {command_str}")

        # --- FIX: We use subprocess.run HERE to capture output ---
        try:
            # We need shell=True and zsh to load your '.zshrc' for the 'say' command
            full_command = f'source ~/.zshrc && {command_str}'

            result = subprocess.run(
                full_command,
                shell=True,
                executable="/usr/bin/zsh", # Important for 'say'
                capture_output=True,
                text=True,
                timeout=10,
                check=True # Raise an error if the command fails
            )

            # Success: Combine stdout and stderr
            output = result.stdout
            if result.stderr:
                # Zsh startup can be noisy, but we'll include stderr just in case
                output += f"\nSTDERR: {result.stderr}"

            # Log a snippet of the captured output
            print(f"✅ Output captured. Sending to frontend. (Snippet: {output.strip()[:70]}...)")

            # Send the output back to Tampermonkey
            return jsonify({'status': 'success', 'output': output})

        except subprocess.CalledProcessError as e:
            # Command fail hui
            error_output = e.stderr or e.stdout
            print(f"❌ Execution failed (CalledProcessError): {error_output}")
            return jsonify({'status': 'error', 'output': error_output})
        except Exception as e:
            print(f"❌ Execution failed (Exception): {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
        # --- End of FIX ---

    else:
        # Not in whitelist
        print(f"Command not in whitelist: {command_str}")
        return jsonify({"status": "confirmation_required", "message": "Command not whitelisted"}), 403

    # The old "dead code" block is now removed.

@app.route('/whitelist', methods=['POST'])
def manage_whitelist():
    data = request.json
    command_str = data.get('command')
    if not command_str:
        return jsonify({"status": "error", "message": "No command provided"}), 400

    add_to_whitelist(command_str)
    print(f"Added to whitelist (Exact): {command_str}")
    return jsonify({"status": "success", "message": "Command added to whitelist"}), 200

if __name__ == '__main__':
    print("--- Starting Local Command Server (v1.3 - Output Capture Fix) ---")
    print(f"Whitelist file located at: {os.path.abspath(WHITELIST_FILE)}")
    print("Waiting for frontend script to connect...")
    app.run(host='127.0.0.1', port=5000)
