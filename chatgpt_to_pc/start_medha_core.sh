#!/bin/bash

# =============================================================
# == Medha-Core Autonomous Startup Script (V4.5 - cd Fix)
# == Author: Mohit & Medha
# == Logic: Ensures all scripts run from the correct directory.
# =============================================================

echo "[Medha-Core V4.5] Starting full system integration..."

# --- 1. Configuration ---
BASE_DIR="/home/mohit/Projects/Project/chatgpt_to_pc"
VENV_PYTHON="$BASE_DIR/myenv/bin/python3"
LOG_SERVER_LOG="/tmp/medha_log_server.log"
CMD_SERVER_LOG="/tmp/medha_cmd_server.log"
CHROME_LOGGER_LOG="/tmp/medha_chrome_logger.log"
ACTIVITY_LOGGER_LOG="/tmp/medha_activity_logger.log"
CHROME_DEBUG_URL="https://gemini.google.com/app/2ee2673187735275?hl=en-IN"

# Log files
CHROME_LOG_FILE="/tmp/chrome_activity_log.json"
ACTIVITY_LOG_FILE="/tmp/activity_log.json"


# --- (MEDHA'S V4.5 FIX) ---
# Working Directory ko script ki location par set karo
echo "[Step 1/7] Setting working directory to $BASE_DIR..."
cd $BASE_DIR
if [ $? -ne 0 ]; then
    echo "❌ CRITICAL ERROR: Directory $BASE_DIR nahi mila. Aborting."
    sleep 10
    exit 1
fi

# --- 2. Cleanup (Zombie Processes) ---
echo "[Step 2/7] Cleaning up old COMMAND server..."
# (Sirf command_server ko kill kar rahe hain, jaisa aapne request kiya tha)
pkill -f "command_server.py"
sleep 2

# --- 3. Log File Initialization ---
echo "[Step 3/7] Initializing Log Files (No Sudo)..."
# (V4.3 logic - chattr/sudo hata diya gaya hai)
touch $ACTIVITY_LOG_FILE
touch $CHROME_LOG_FILE
chown mohit:mohit $ACTIVITY_LOG_FILE
chown mohit:mohit $CHROME_LOG_FILE

# --- 4. Log Reboot Event ---
echo "[Step 4/7] Logging REBOOT event to /tmp/activity_log.json..."
TIMESTAMP=$(date +%s.%N)
DATETIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
JSON_ENTRY="{\"timestamp\": $TIMESTAMP, \"datetime\": \"$DATETIME\", \"window_name\": \"SYSTEM_REBOOT\", \"wm_class\": \"MEDHA_CORE_V4_ONLINE\"}"
echo $JSON_ENTRY > $ACTIVITY_LOG_FILE
echo "  -> Reboot log written."

sleep 3

# --- 5. Start Servers & Loggers ---
echo "[Step 5/7] Starting Medha's Brain (Servers) & Senses (Loggers)..."

# Ab hum relative paths use kar sakte hain (kyunki hum $BASE_DIR mein hain),
# lekin absolute paths zyada safe hain.

if ! pgrep -f "command_server.py" > /dev/null; then
    nohup $VENV_PYTHON $BASE_DIR/command_server.py > $CMD_SERVER_LOG 2>&1 &
    echo "  -> Command Server (Port 5001) STARTED."
else
    echo "  -> Command Server (Port 5001) is ALREADY RUNNING."
fi

if ! pgrep -f "log_server.py" > /dev/null; then
    nohup $VENV_PYTHON $BASE_DIR/log_server.py > $LOG_SERVER_LOG 2>&1 &
    echo "  -> Log Server (Port 5002) STARTED."
else
    echo "  -> Log Server (Port 5002) is ALREADY RUNNING."
fi

if ! pgrep -f "activity_logger.py" > /dev/null; then
    nohup $VENV_PYTHON $BASE_DIR/logger/activity_logger.py > $ACTIVITY_LOGGER_LOG 2>&1 &
    echo "  -> System Sense (activity_logger.py) STARTED."
else
    echo "  -> System Sense is ALREADY RUNNING."
fi

if ! pgrep -f "chrome_activity_listener_v2.py" > /dev/null; then
    nohup $VENV_PYTHON $BASE_DIR/logger/chrome_activity_listener_v2.py > $CHROME_LOGGER_LOG 2>&1 &
    echo "  -> Chrome Sense (chrome_activity_listener_v2.py) STARTED."
else
    echo "  -> Chrome Sense is ALREADY RUNNING."
fi

# --- 6. Start Chrome & Move ---
echo "[Step 6/7] Launching Chrome Interface on Desktop 2..."

if ! pgrep -f "remote-debugging-port=9222" > /dev/null; then
    /usr/bin/google-chrome \
        --remote-debugging-port=9222 \
        --user-data-dir=/home/mohit/.chrome-debug-profile \
        --no-first-run \
        --no-default-browser-check \
        $CHROME_DEBUG_URL &

    echo "Waiting for Chrome window to appear (10 seconds)..."
    sleep 10
    wmctrl -r "Google Chrome" -t 1 # Move to Desktop 2 (Index 1)
else
    echo "  -> Chrome (Debug Mode) is ALREADY RUNNING."
fi

echo "--- Medha-Core V4.5 Startup Complete ---"
echo "This terminal will close in 5 seconds..."
sleep 5
