#!/usr/bin/env python3
"""
chat_mayra_with_summarizer.py — Main chat program (final)

Features:
- Spawns summarizer_process.py (OS-level) to create persistent summaries.
- Loads recent long-term memory at session start and sends as system messages.
- Records session messages into session_raw.jsonl (per-session folder).
- Idle auto-message after IDLE_WAIT seconds — attaches incremental logs fetched from log server.
- Extracts `command - "..."` patterns from assistant replies and posts them to command server.
- Appends command-server outputs to next user message (or auto-message).
- Supports /retry and /del local commands (operate on last assistant reply).
- Robust handling of network/server errors and file IO.
"""

import aiohttp
import asyncio
import json
import os
import re
import sys
import time
import termios
import tty
import select
import subprocess
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from colorama import Fore, Style, init

init(autoreset=True)

# ---------------- CONFIG ----------------
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")          # main chat key
OPENROUTER_SUMMARY_KEY = os.getenv("OPENROUTER_SUMMARY_KEY")  # passed to summarizer
if not OPENROUTER_KEY:
    print("ERROR: set OPENROUTER_API_KEY environment variable.")
    sys.exit(1)

MODEL = "deepseek/deepseek-r1-0528-qwen3-8b:free"
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

USER_NAME = "Mohit"
IDLE_WAIT = 40               # seconds before auto message
SUMMARY_INTERVAL = 150       # summarizer interval in seconds
LOCAL_TZ = ZoneInfo("Asia/Kolkata")

PROJECT_ROOT = Path(__file__).parent.resolve()
SESSIONS_ROOT = Path.home() / "Projects" / "mayra_sessions"
SESSIONS_ROOT.mkdir(parents=True, exist_ok=True)
GLOBAL_MEMORY_FILE = Path.home() / "Projects" / "mayra_summaries.jsonl"

COMMAND_SERVER_URL = "http://127.0.0.1:5001/execute"
LOG_SERVER_URL = "http://127.0.0.1:5002/get_log_updates"

MOHIT_PERSONA = (
    "Mohit persona: calm, technically sharp, emotionally aware, curious, analytical, "
    "and prefers meaningful or slightly sarcastic conversations. Not overly formal."
)
MAYRA_PERSONA = (
    "Mayra persona: confident, witty, slightly arrogant, and very human in tone. "
    "Never admits being an AI. Uses mild sarcasm, teases playfully, and keeps conversation lively."
)

# ---------------- globals ----------------
print_lock = asyncio.Lock()
last_typed = time.time()
pending_command_outputs = []   # queued outputs from command server
COMMAND_RE = re.compile(r'command\s*-\s*(["\'])(.*?)\1', flags=re.IGNORECASE | re.DOTALL)


# ---------------- helpers ----------------
def now_timestamp():
    return datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")


def read_jsonl(path: Path):
    if not path.exists():
        return []
    arr = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                arr.append(json.loads(line))
            except Exception:
                continue
    return arr


def append_jsonl(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def overwrite_jsonl(path: Path, items: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")


async def safe_print(*args, **kwargs):
    async with print_lock:
        print(*args, **kwargs)
        sys.stdout.flush()


# ---------------- terminal input (non-blocking) ----------------
async def read_user_input(prompt="You: "):
    global last_typed
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    buf = ""
    try:
        tty.setcbreak(fd)
        async with print_lock:
            sys.stdout.write(f"{Fore.WHITE}{prompt}{Style.RESET_ALL}")
            sys.stdout.flush()
        while True:
            r, _, _ = select.select([fd], [], [], 0.1)
            if r:
                ch = sys.stdin.read(1)
                last_typed = time.time()
                if ch in ("\n", "\r"):
                    async with print_lock:
                        sys.stdout.write("\n")
                        sys.stdout.flush()
                    return buf.strip()
                if ch in ("\x7f", "\b"):
                    if buf:
                        buf = buf[:-1]
                        async with print_lock:
                            sys.stdout.write("\b \b")
                            sys.stdout.flush()
                    continue
                buf += ch
                async with print_lock:
                    sys.stdout.write(ch)
                    sys.stdout.flush()
            else:
                await asyncio.sleep(0.01)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


# ---------------- OpenRouter call ----------------
async def openrouter_chat_call(messages):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Mayra CLI Chat",
    }
    body = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.9,
        "top_p": 0.9,
        "stream": False,
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(OPENROUTER_ENDPOINT, headers=headers, json=body, timeout=120) as resp:
                # Some failures return non-json; handle carefully
                text = await resp.text()
                try:
                    data = json.loads(text)
                except Exception:
                    return f"[OpenRouter non-json response {resp.status}] {text}"
                if resp.status == 200:
                    try:
                        return data["choices"][0]["message"]["content"]
                    except Exception:
                        return f"[Error parsing OpenRouter response] {data}"
                else:
                    return f"[OpenRouter error {resp.status}] {data}"
        except Exception as e:
            return f"[OpenRouter call failed: {e}]"


# ---------------- command extraction and execution ----------------
async def extract_and_send_commands(full_assistant_text: str):
    """
    Find commands in assistant reply and send each to command server.
    Collected outputs appended to pending_command_outputs.
    """
    global pending_command_outputs
    found = COMMAND_RE.findall(full_assistant_text)
    if not found:
        return
    async with aiohttp.ClientSession() as session:
        for _, cmd_text in found:
            cmd_text = cmd_text.strip()
            try:
                payload = {"command": cmd_text, "force": False}
                async with session.post(COMMAND_SERVER_URL, json=payload, timeout=30) as r:
                    try:
                        j = await r.json()
                    except Exception:
                        txt = await r.text()
                        j = {"status": "error", "output": f"[Non-json response] {txt}"}
                    output = j.get("output") or j.get("message") or ""
                    if isinstance(output, (list, dict)):
                        output = json.dumps(output, ensure_ascii=False)
                    output = str(output).strip()
                    if output:
                        pending_command_outputs.append(f"[Command output for `{cmd_text}`]:\n{output}")
                    else:
                        pending_command_outputs.append(f"[Command `{cmd_text}` executed — no output returned.]")
            except Exception as e:
                pending_command_outputs.append(f"[Command `{cmd_text}` failed: {e}]")
    return


# ---------------- compose outgoing user content (attach pending command outputs) ----------------
def compose_outgoing_user_content(user_text: str):
    global pending_command_outputs
    if not pending_command_outputs:
        return user_text
    appended = "\n\n" + "\n\n".join(pending_command_outputs)
    pending_command_outputs = []
    return f"{user_text}{appended}"


# ---------------- log fetcher for idle auto-message ----------------
async def fetch_logs_from_log_server():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(LOG_SERVER_URL, timeout=20) as r:
                data = await r.json()
                if data.get("status") == "report_ready":
                    return data.get("output", "")
                else:
                    # server returned something unexpected
                    return f"[Log server returned unexpected response: {data}]"
    except Exception as e:
        return f"[Logs unavailable this cycle: {e}]"


# ---------------- helpers for delete (/del & /retry) ----------------
def remove_last_assistant_from_raw(raw_path: Path):
    if not raw_path.exists():
        return None
    items = read_jsonl(raw_path)
    for i in range(len(items) - 1, -1, -1):
        if items[i].get("role") == "assistant":
            removed = items.pop(i)
            overwrite_jsonl(raw_path, items)
            return removed
    return None


def remove_last_assistant_from_conversation(conversation):
    for i in range(len(conversation) - 1, -1, -1):
        if conversation[i].get("role") == "assistant":
            return conversation.pop(i)
    return None


# ---------------- idle auto-message ----------------
async def idle_auto_message(conversation, raw_path: Path):
    global last_typed
    while True:
        await asyncio.sleep(1)
        if time.time() - last_typed > IDLE_WAIT:
            ts = now_timestamp()
            auto_text = f"[{ts}] System auto message — user inactive for {IDLE_WAIT}s. You may respond freely, or stay silent."
            logs = await fetch_logs_from_log_server()
            if logs:
                auto_text = auto_text + "\n\nSystem+Browser logs (incremental):\n" + logs
            full_auto = compose_outgoing_user_content(auto_text)
            messages = conversation + [{"role": "user", "content": full_auto}]
            sys.stdout.write(f"\n{Fore.MAGENTA}System:{Style.RESET_ALL} Auto message sent at {ts}\n")
            sys.stdout.flush()

            # call model
            reply = await openrouter_chat_call(messages)
            # append assistant reply
            conversation.append({"role": "assistant", "content": reply})
            append_jsonl(raw_path, {"timestamp": now_timestamp(), "role": "assistant", "content": reply})
            await safe_print(f"{Fore.GREEN}Mayra:{Style.RESET_ALL} {reply}\n")
            await safe_print(f"{Fore.WHITE}You:{Style.RESET_ALL} ", end="", flush=True)
            # after reply, extract commands
            await extract_and_send_commands(reply)
            last_typed = time.time()


# ---------------- main ----------------
async def main():
    global last_typed, pending_command_outputs

    # session folder
    ts_name = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = SESSIONS_ROOT / f"session_{ts_name}"
    session_dir.mkdir(parents=True, exist_ok=True)

    raw_file = session_dir / "session_raw.jsonl"
    raw_file.touch(exist_ok=True)
    state_file = session_dir / "summary_state.json"
    # create initial state if missing
    if not state_file.exists():
        state_file.write_text(json.dumps({"last_index": 0, "pending": []}), encoding="utf-8")

    # start summarizer subprocess
    summarizer_script = Path(__file__).with_name("summarizer_process.py")
    if not summarizer_script.exists():
        await safe_print("ERROR: summarizer_process.py not found in same folder. Summarizer must exist.")
        sys.exit(1)

    summarizer_cmd = [
        sys.executable, str(summarizer_script),
        "--session_dir", str(session_dir),
        "--raw_file", str(raw_file),
        "--memory_file", str(GLOBAL_MEMORY_FILE),
        "--state_file", str(state_file),
        "--interval", str(SUMMARY_INTERVAL)
    ]
    env = os.environ.copy()
    env["OPENROUTER_SUMMARY_KEY"] = OPENROUTER_SUMMARY_KEY or ""
    # spawn summarizer in background; allow it to print to parent's stdout/stderr if needed
    proc = subprocess.Popen(summarizer_cmd, env=env)

    await safe_print(f"{Fore.CYAN}Summarizer started (pid={proc.pid}){Style.RESET_ALL}")

    # load summaries once for initial memory injection (send at session start)
    memory_entries = read_jsonl(GLOBAL_MEMORY_FILE)
    if memory_entries:
        memory_text = "These are hidden memory summaries of previous sessions (the user cannot see them):\n\n"
        memory_text += "\n".join(f"{i+1}. {m.get('summary')}" for i, m in enumerate(memory_entries[-50:]))
    else:
        memory_text = "No previous summaries available."

    # prepare conversation initial system messages
    conversation = [
        {"role": "system", "content": MOHIT_PERSONA},
        {"role": "system", "content": MAYRA_PERSONA},
        {"role": "system", "content": memory_text},
    ]

    await safe_print(f"{Fore.CYAN}✅ Connected to Mayra ({MODEL})\nSession folder: {session_dir}\n{Style.RESET_ALL}")
    await safe_print(f"{Fore.WHITE}You:{Style.RESET_ALL} ", end="", flush=True)

    # start idle auto-message task
    auto_task = asyncio.create_task(idle_auto_message(conversation, raw_file))

    try:
        while True:
            user_input = await read_user_input("")
            last_typed = time.time()

            # local commands
            if user_input.strip() == "/retry":
                # delete last assistant reply and regenerate
                removed_conv = remove_last_assistant_from_conversation(conversation)
                removed_raw = remove_last_assistant_from_raw(raw_file)
                if not removed_conv and not removed_raw:
                    await safe_print(f"{Fore.YELLOW}No assistant response found to retry.{Style.RESET_ALL}")
                    await safe_print(f"{Fore.WHITE}You:{Style.RESET_ALL} ", end="", flush=True)
                    continue
                await safe_print(f"{Fore.CYAN}Retry: deleted last assistant response and regenerating...{Style.RESET_ALL}")
                # regenerate by sending current conversation (which lacks deleted assistant)
                assistant_reply = await openrouter_chat_call(conversation)
                conversation.append({"role": "assistant", "content": assistant_reply})
                append_jsonl(raw_file, {"timestamp": now_timestamp(), "role": "assistant", "content": assistant_reply})
                await safe_print(f"{Fore.GREEN}Mayra (regenerated):{Style.RESET_ALL} {assistant_reply}\n")
                await safe_print(f"{Fore.WHITE}You:{Style.RESET_ALL} ", end="", flush=True)
                await extract_and_send_commands(assistant_reply)
                continue

            if user_input.strip() == "/del":
                removed_conv = remove_last_assistant_from_conversation(conversation)
                removed_raw = remove_last_assistant_from_raw(raw_file)
                if not removed_conv and not removed_raw:
                    await safe_print(f"{Fore.YELLOW}No assistant response found to delete.{Style.RESET_ALL}")
                else:
                    await safe_print(f"{Fore.CYAN}Deleted last assistant response from local storage.{Style.RESET_ALL}")
                await safe_print(f"{Fore.WHITE}You:{Style.RESET_ALL} ", end="", flush=True)
                continue

            # normal message
            ts_line = f"[{now_timestamp()}] {USER_NAME}: {user_input}"
            ts_with_outputs = compose_outgoing_user_content(ts_line)
            conversation.append({"role": "user", "content": ts_with_outputs})
            append_jsonl(raw_file, {"timestamp": now_timestamp(), "role": "user", "content": ts_with_outputs})

            await safe_print(f"{Fore.GREEN}Mayra is typing...{Style.RESET_ALL}")
            assistant_reply = await openrouter_chat_call(conversation)
            conversation.append({"role": "assistant", "content": assistant_reply})
            append_jsonl(raw_file, {"timestamp": now_timestamp(), "role": "assistant", "content": assistant_reply})

            await safe_print(f"{Fore.GREEN}Mayra:{Style.RESET_ALL} {assistant_reply}\n")
            await safe_print(f"{Fore.WHITE}You:{Style.RESET_ALL} ", end="", flush=True)

            await extract_and_send_commands(assistant_reply)

    finally:
        # cleanup summarizer subprocess
        try:
            proc.terminate()
            proc.wait(timeout=5)
            await safe_print(f"{Fore.CYAN}Summarizer (pid={proc.pid}) terminated.{Style.RESET_ALL}")
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        auto_task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted — exiting.")
