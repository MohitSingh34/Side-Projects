#!/usr/bin/env python3
"""
Main chat program (final version).
- Starts OS-level summarizer (separate script) for background summary creation.
- Loads summaries once at session start and injects them as hidden system context.
- Sends user messages to OpenRouter model and gets full replies.
- Extracts commands from assistant replies of the form: command - "..." or command - '...'
  and POSTs them to local command-server (/execute). Responses from command-server are queued
  and appended to next user message or auto-message.
- Idle auto-message after IDLE_WAIT seconds (no summaries included mid-session).
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
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_SUMMARY_KEY = os.getenv("OPENROUTER_SUMMARY_KEY")  # used by summarizer process
if not OPENROUTER_KEY:
    print("ERROR: set OPENROUTER_API_KEY")
    sys.exit(1)

MODEL = "deepseek/deepseek-r1-0528-qwen3-8b:free"
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

USER_NAME = "Mohit"
IDLE_WAIT = 40               # seconds before auto message
SUMMARY_INTERVAL = 150       # summarizer runs every 150s (handled by summarizer process)
LOCAL_TZ = ZoneInfo("Asia/Kolkata")

# paths
PROJECT_ROOT = Path(__file__).parent.resolve()
SESSIONS_ROOT = Path.home() / "Projects" / "mayra_sessions"
SESSIONS_ROOT.mkdir(parents=True, exist_ok=True)
GLOBAL_MEMORY_FILE = Path.home() / "Projects" / "mayra_summaries.jsonl"

# command server settings (must be running)
COMMAND_SERVER_URL = "http://127.0.0.1:5001/execute"

# personalities
MOHIT_PERSONA = (
    "Mohit persona: calm, technically sharp, emotionally aware, curious, analytical, "
    "and prefers meaningful or slightly sarcastic conversations. Not overly formal."
)
MAYRA_PERSONA = (
    "Mayra persona: confident, witty, slightly arrogant, and very human in tone. "
    "Never admits being an AI. Uses mild sarcasm, teases playfully, and keeps conversation lively."
)

# ---------------- Globals ----------------
print_lock = asyncio.Lock()
last_typed = time.time()
pending_command_outputs = []   # queue of strings returned from command server, appended to next user/auto message

# ---------------- Helpers ----------------
def now_timestamp():
    return datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")


def append_raw_message(path: Path, role: str, content: str):
    """Append single JSON line to session_raw.jsonl."""
    entry = {"timestamp": now_timestamp(), "role": role, "content": content}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_summaries():
    """Load up to 50 summaries from global memory file (if exists)."""
    if not GLOBAL_MEMORY_FILE.exists():
        return []
    lines = [l.strip() for l in GLOBAL_MEMORY_FILE.open("r", encoding="utf-8") if l.strip()]
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except:
            continue
    return out[-50:]


async def safe_print(*args, **kwargs):
    async with print_lock:
        print(*args, **kwargs)
        sys.stdout.flush()


# ---------------- Terminal input (non-blocking, real-time) ----------------
async def read_user_input(prompt="You: "):
    global last_typed
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    buffer = ""
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
                    return buffer.strip()
                if ch in ("\x7f", "\b"):
                    if buffer:
                        buffer = buffer[:-1]
                        async with print_lock:
                            sys.stdout.write("\b \b")
                            sys.stdout.flush()
                    continue
                buffer += ch
                async with print_lock:
                    sys.stdout.write(ch)
                    sys.stdout.flush()
            else:
                await asyncio.sleep(0.01)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


# ---------------- OpenRouter call (non-streaming for full response capture) ----------------
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
        "stream": False
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(OPENROUTER_ENDPOINT, headers=headers, json=body, timeout=120) as resp:
            data = await resp.json()
            try:
                return data["choices"][0]["message"]["content"]
            except Exception:
                return f"[Error parsing response] {data}"


# ---------------- Command extraction & execution ----------------
COMMAND_RE = re.compile(r'command\s*-\s*(["\'])(.*?)\1', flags=re.IGNORECASE | re.DOTALL)

async def extract_and_send_commands(full_assistant_text: str):
    """
    Find all commands from assistant text and POST them (one by one) to command server.
    Collected outputs appended to global pending_command_outputs.
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
                        j = {"status": "error", "output": f"[Command server non-json response: {await r.text()}]"}
                    status = j.get("status")
                    output = j.get("output") or j.get("message") or ""
                    # Normalize output to string
                    if isinstance(output, (list, dict)):
                        output = json.dumps(output, ensure_ascii=False)
                    output = str(output).strip()
                    if output:
                        pending_command_outputs.append(f"[Command output for `{cmd_text}`]:\n{output}")
                    else:
                        # If empty, still append a small note so flow doesn't break
                        pending_command_outputs.append(f"[Command `{cmd_text}` executed — no output returned.]")
            except Exception as e:
                pending_command_outputs.append(f"[Command `{cmd_text}` failed to execute: {e}]")
    return


# ---------------- Compose message to send (append pending command outputs if any) ----------------
def compose_outgoing_user_content(user_text: str):
    """Append any pending command outputs to the user_text, clear queue."""
    global pending_command_outputs
    if not pending_command_outputs:
        return user_text
    appended = "\n\n" + "\n\n".join(pending_command_outputs)
    # clear after attaching
    pending_command_outputs = []
    return f"{user_text}{appended}"


# ---------------- Idle auto-message ----------------
async def idle_auto_message(conversation, raw_file):
    """
    If user is idle for IDLE_WAIT seconds, auto-send a system prompt (no summaries),
    but append any pending command outputs as required.
    """
    global last_typed
    while True:
        await asyncio.sleep(1)
        if time.time() - last_typed > IDLE_WAIT:
            ts = now_timestamp()
            auto_text = f"[{ts}] System auto message — user inactive for {IDLE_WAIT}s. You may respond freely, or stay silent."
            # attach pending outputs
            full_auto = compose_outgoing_user_content(auto_text)
            messages = conversation + [{"role": "user", "content": full_auto}]
            sys.stdout.write(f"\n{Fore.MAGENTA}System:{Style.RESET_ALL} Auto message sent at {ts}\n")
            sys.stdout.flush()
            reply = await openrouter_chat_call(messages)
            append_raw_message(raw_file, "assistant", reply)
            await safe_print(f"{Fore.GREEN}Mayra:{Style.RESET_ALL} {reply}\n")
            await safe_print(f"{Fore.WHITE}You:{Style.RESET_ALL} ", end="", flush=True)
            last_typed = time.time()


# ---------------- Main ----------------
async def main():
    global last_typed, pending_command_outputs
    # create session folder
    ts_for_name = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = SESSIONS_ROOT / f"session_{ts_for_name}"
    session_dir.mkdir(parents=True, exist_ok=True)

    raw_file = session_dir / "session_raw.jsonl"
    raw_file.touch(exist_ok=True)
    state_file = session_dir / "summary_state.json"
    state_file.write_text(json.dumps({"last_index": 0}), encoding="utf-8")

    # start summarizer subprocess (OS-level)
    summarizer_script = Path(__file__).with_name("summarizer_process.py")
    if not summarizer_script.exists():
        await safe_print("ERROR: summarizer_process.py missing in same folder.")
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

    proc = subprocess.Popen(summarizer_cmd, env=env)
    await safe_print(f"{Fore.CYAN}Summarizer started (pid={proc.pid}){Style.RESET_ALL}")

    # load summaries once and build memory_text
    summaries = read_summaries()
    if summaries:
        memory_text = "These are hidden memory summaries of previous sessions (the user cannot see them):\n\n"
        memory_text += "\n".join(f"{i+1}. {s['summary']}" for i, s in enumerate(summaries))
    else:
        memory_text = "No previous summaries available."

    # initial conversation: two personalities + hidden memory_text
    conversation = [
        {"role": "system", "content": MOHIT_PERSONA},
        {"role": "system", "content": MAYRA_PERSONA},
        {"role": "system", "content": memory_text},
    ]

    await safe_print(f"{Fore.CYAN}✅ Connected to Mayra ({MODEL})\nSession folder: {session_dir}\n{Style.RESET_ALL}")
    await safe_print(f"{Fore.WHITE}You:{Style.RESET_ALL} ", end="", flush=True)

    # start idle_auto_message task
    auto_task = asyncio.create_task(idle_auto_message(conversation, raw_file))

    try:
        while True:
            user_input = await read_user_input("")
            last_typed = time.time()

            if user_input.lower() in ("exit", "quit"):
                await safe_print(f"{Fore.CYAN}Exiting chat...{Style.RESET_ALL}")
                break

            # compose content with pending command outputs appended
            full_user_content = compose_outgoing_user_content(f"[{now_timestamp()}] {USER_NAME}: {user_input}")

            # append to conversation and raw file (user)
            conversation.append({"role": "user", "content": full_user_content})
            append_raw_message(raw_file, "user", full_user_content)

            # send to model and get full reply
            await safe_print(f"{Fore.GREEN}Mayra is typing...{Style.RESET_ALL}")
            assistant_reply = await openrouter_chat_call(conversation)
            # append reply to conversation & raw file
            conversation.append({"role": "assistant", "content": assistant_reply})
            append_raw_message(raw_file, "assistant", assistant_reply)

            # print assistant reply
            await safe_print(f"{Fore.GREEN}Mayra:{Style.RESET_ALL} {assistant_reply}\n")
            await safe_print(f"{Fore.WHITE}You:{Style.RESET_ALL} ", end="", flush=True)

            # After full assistant reply, extract any commands and send to command server
            await extract_and_send_commands(assistant_reply)

    finally:
        # cleanup: stop summarizer
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
