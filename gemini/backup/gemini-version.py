#!/usr/bin/env python3

import aiohttp
import asyncio
import json
import os
import re
import subprocess
import sys
import termios
import tty
import select
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from colorama import Fore, Style, init

init(autoreset=True)

# ---------------- CONFIG ----------------
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print(f"{Fore.RED}ERROR:{Style.RESET_ALL} GEMINI_API_KEY not set.")
    sys.exit(1)

MODEL = "gemini-2.5-flash"
GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

LOG_SERVER_URL = "http://127.0.0.1:5002/get_log_updates"
COMMAND_SERVER_URL = "http://127.0.0.1:5001/execute"

USER_NAME = "Mohit"
LOCAL_TZ = ZoneInfo("Asia/Kolkata")

# Timers
IDLE_WAIT = 50
LOG_FETCH_AHEAD = 10
SUMMARIZER_INTERVAL = 150

# Workspace & files
ROOT = Path.home() / "Projects" / "mayra_sessions_gemini"
ROOT.mkdir(parents=True, exist_ok=True)
SESSION = ROOT / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
SESSION.mkdir(parents=True, exist_ok=True)
RAW_FILE = SESSION / "session_raw.jsonl"
RAW_FILE.touch(exist_ok=True)
MEMORY_FILE = Path.home() / "Projects" / "mayra_memory_gemini.jsonl"
STATE_FILE = SESSION / "summarizer_state.json"

SUMMARIZER_SCRIPT = Path(__file__).with_name("summarizer_gemini.py")

# Multiline-capable command extractor:
# Supports:
#   command - """..."""
#   command - '''...'''
#   command - ```...```
#   command - "..."
#   command - '...'
CMD_RE = re.compile(
    r'command\s*-\s*(?P<quote>"""|\'\'\'|```|"|\')(?P<cmd>.*?)(?P=quote)',
    flags=re.IGNORECASE | re.DOTALL
)

# ---------------- GLOBALS ----------------
print_lock = asyncio.Lock()
conversation = []
last_typed = time.time()
pending_command_outputs = []   # legacy; rarely used
logs_ready_for_send = ""
summarizer_proc = None

# ---------------- helpers ----------------
def now_ts():
    return datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")

def append_jsonl(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

async def safe_print(*a, **kw):
    async with print_lock:
        print(*a, **kw)
        sys.stdout.flush()

# ---------------- Gemini helpers ----------------
def build_gemini_body(messages):
    """
    Map roles: system->user, user->user, assistant->model
    Each content -> {"parts":[{"text":...}]} or {"role":"model","parts":[...]}
    """
    role_map = {"system": "user", "assistant": "model", "user": "user"}
    contents = []
    for m in messages:
        role = role_map.get(m.get("role"), "user")
        txt = m.get("content", "")
        part = {"text": txt}
        if role == "user":
            contents.append({"parts": [part]})
        else:
            contents.append({"role": role, "parts": [part]})
    return {"contents": contents}

async def call_gemini(messages, timeout=90):
    """Call Gemini generateContent REST endpoint and return concatenated text results."""
    body = build_gemini_body(messages)
    try:
        async with aiohttp.ClientSession() as ses:
            async with ses.post(GEMINI_ENDPOINT, json=body, timeout=timeout) as resp:
                text = await resp.text()
                try:
                    data = json.loads(text)
                except Exception:
                    return f"[Gemini returned non-JSON: {text}]"
                texts = []
                def walk(o):
                    if isinstance(o, dict):
                        if "text" in o and isinstance(o["text"], str):
                            texts.append(o["text"])
                        for v in o.values():
                            walk(v)
                    elif isinstance(o, list):
                        for e in o:
                            walk(e)
                walk(data)
                joined = " ".join(t.strip() for t in texts).strip()
                if joined:
                    return joined
                return f"[Gemini returned no text; raw: {json.dumps(data, ensure_ascii=False)}]"
    except asyncio.TimeoutError:
        return "[Gemini call timed out]"
    except Exception as e:
        return f"[Gemini call failed: {e}]"

# ---------------- Log server fetch and structure ----------------
async def fetch_logs_raw():
    try:
        async with aiohttp.ClientSession() as ses:
            async with ses.get(LOG_SERVER_URL, timeout=12) as r:
                j = await r.json()
                if isinstance(j, dict):
                    return j.get("output", "") or ""
                return str(j)
    except Exception:
        return ""

def structure_logs(raw):
    if not raw:
        return ""
    if "-----------------------system" in raw:
        left, right = raw.split("-----------------------system", 1)
        chrome_part = left.strip()
        system_part = right.strip()
    else:
        chrome_part = raw.strip()
        system_part = ""
    structured = (
        "These are the Chrome and System logs sent automatically to let you know the current laptop and browsing state.\n\n"
        "------------------- Chrome Logs -------------------\n"
        f"{chrome_part}\n\n"
        "------------------- System Logs -------------------\n"
        f"{system_part}"
    )
    return structured

async def fetch_logs_structured():
    raw = await fetch_logs_raw()
    return structure_logs(raw)

# ---------------- Command server integration ----------------
async def send_command_to_server(cmd_text, timeout=30):
    payload = {"command": cmd_text, "force": False}
    try:
        async with aiohttp.ClientSession() as ses:
            async with ses.post(COMMAND_SERVER_URL, json=payload, timeout=timeout) as r:
                try:
                    j = await r.json()
                    return j
                except Exception:
                    t = await r.text()
                    return {"status":"error","output": t}
    except Exception as e:
        return {"status":"error","output": str(e)}

async def run_command_and_forward_output(cmd_text):
    """
    Execute command on backend, get the output, send that output to Gemini as a user message,
    then call Gemini and store/print the reply (full).
    """
    resp = await send_command_to_server(cmd_text)
    # normalize output
    if isinstance(resp, dict):
        out_text = resp.get("output") or resp.get("message") or resp.get("error") or json.dumps(resp, ensure_ascii=False)
    else:
        out_text = str(resp)
    ts = now_ts()
    user_block = f"[{ts}] System command output for `{cmd_text}`\n$ {cmd_text}\n{out_text}"
    # save and append to conversation so Gemini has context
    append_jsonl(RAW_FILE, {"timestamp": ts, "role": "system_command_output", "content": user_block})
    conversation.append({"role": "user", "content": user_block})
    await safe_print(f"\n{Fore.MAGENTA}→ Command executed: {cmd_text}{Style.RESET_ALL}")
    # call Gemini and get full reply
    reply = await call_gemini(conversation)
    conversation.append({"role": "assistant", "content": reply})
    append_jsonl(RAW_FILE, {"timestamp": now_ts(), "role": "assistant", "content": reply})
    # after storing, search for any further commands in this new reply (recursive)
    await extract_and_handle_commands(reply)
    # print GEMINI reply
    await safe_print(f"{Fore.GREEN}Mayra:{Style.RESET_ALL} {reply}\n")
    return reply

# ---------------- Command extractor + handling ----------------
async def extract_and_handle_commands(assistant_text):
    """
    Extract all command blocks (multiline included) from assistant_text and run them.
    Each found command is executed and its output forwarded to Gemini immediately.
    """
    matches = list(CMD_RE.finditer(assistant_text))
    if not matches:
        return []
    results = []
    for m in matches:
        cmd = m.group("cmd").strip()
        # execute and forward
        try:
            await run_command_and_forward_output(cmd)
            results.append({"command": cmd, "status": "executed"})
        except Exception as e:
            # fallback: queue output (legacy) so next user message includes it
            block = f"$ {cmd}\n[Command execution failed: {e}]"
            pending_command_outputs.append(block)
            results.append({"command": cmd, "status": "queued_on_error", "error": str(e)})
    return results

# ---------------- Terminal input (first-keypress detection) ----------------
async def read_user_input_with_log_capture(prompt="You: "):
    """
    On first keypress, fetch logs asynchronously.
    Returns: (typed_line, logs_captured)
    The function itself prints the prompt and handles backspace.
    """
    global last_typed
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    buf = ""
    first_key = False
    log_task = None
    fetched_logs = ""
    try:
        tty.setcbreak(fd)
        sys.stdout.write(prompt)
        sys.stdout.flush()
        while True:
            r, _, _ = select.select([fd], [], [], 0.1)
            if r:
                ch = sys.stdin.read(1)
                if not first_key:
                    first_key = True
                    loop = asyncio.get_event_loop()
                    log_task = loop.create_task(fetch_logs_structured())
                last_typed = time.time()
                if ch in ("\n", "\r"):
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    if log_task:
                        try:
                            fetched_logs = await asyncio.wait_for(log_task, timeout=2.0)
                        except Exception:
                            fetched_logs = ""
                    return buf.strip(), fetched_logs
                if ch in ("\x7f", "\b"):
                    if buf:
                        buf = buf[:-1]
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                    continue
                buf += ch
                sys.stdout.write(ch)
                sys.stdout.flush()
            else:
                await asyncio.sleep(0.01)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

# ---------------- Idle monitor (prefetch + auto-send) ----------------
async def idle_and_prefetch_monitor():
    global last_typed, logs_ready_for_send, pending_command_outputs
    logs_ready_for_send = ""
    while True:
        await asyncio.sleep(1)
        idle = time.time() - last_typed
        # prefetch logs
        if LOG_FETCH_AHEAD > 0 and (IDLE_WAIT - LOG_FETCH_AHEAD - 0.5) < idle < (IDLE_WAIT - LOG_FETCH_AHEAD + 0.5):
            if not logs_ready_for_send:
                logs_ready_for_send = await fetch_logs_structured()
        # auto-send
        if idle >= IDLE_WAIT:
            ts = now_ts()
            auto_text = f"[{ts}] System auto-message due to {int(idle)}s inactivity from Mohit."
            logs_att = logs_ready_for_send or await fetch_logs_structured()
            # --- Mohit's Recovery Protocol ---
            if idle >= 300:  # 5 minutes = 300 seconds
                auto_text = (
                    f"[{ts}] ⚠️ Mohit's Recovery Protocol Triggered ⚠️\n\n"
                    "This message is automatically sending to you because Mohit didn’t type anything "
                    "in the last 5 minutes.\n\n"
                    "Check using your commands if his keyboard is blocked or turned off. "
                    "Mohit can’t reply to Mayra if his keyboard has lost access to the laptop."
                )
            else:
                auto_text = f"[{ts}] System auto-message due to {int(idle)}s inactivity from Mohit."

            # attach logs
            logs_att = logs_ready_for_send or await fetch_logs_structured()
            if logs_att:
                auto_text += "\n\n[Attached logs]\n" + logs_att

            # attach pending commands if any
            if pending_command_outputs:
                auto_text += "\n\n[Pending Command Outputs]\n" + "\n\n".join(pending_command_outputs)
                pending_command_outputs.clear()

            append_jsonl(RAW_FILE, {"timestamp": ts, "role": "user", "content": auto_text})
            conversation.append({"role": "user", "content": auto_text})
            await safe_print(f"\n{Fore.MAGENTA}System:{Style.RESET_ALL} Auto message sent at {ts}\n")
            await safe_print(f"{Fore.GREEN}Mayra is thinking...{Style.RESET_ALL}")
            reply = await call_gemini(conversation)
            conversation.append({"role": "assistant", "content": reply})
            append_jsonl(RAW_FILE, {"timestamp": now_ts(), "role": "assistant", "content": reply})
            # extract commands in this reply (they will be executed and forwarded)
            await extract_and_handle_commands(reply)
            # print reply
            await safe_print(f"{Fore.GREEN}Mayra:{Style.RESET_ALL} {reply}\n")
            logs_ready_for_send = ""
            last_typed = time.time()

# ---------------- Retry helper ----------------
def read_raw_file_lines():
    out = []
    try:
        with RAW_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        pass
    return out

def write_raw_file_lines(lines):
    try:
        with RAW_FILE.open("w", encoding="utf-8") as f:
            for it in lines:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False

async def handle_retry():
    raw = read_raw_file_lines()
    last_idx = None
    for i in range(len(raw)-1, -1, -1):
        if raw[i].get("role") == "assistant":
            last_idx = i
            break
    if last_idx is None:
        await safe_print(f"{Fore.YELLOW}No assistant message found to retry.{Style.RESET_ALL}")
        return
    raw.pop(last_idx)
    if not write_raw_file_lines(raw):
        await safe_print(f"{Fore.RED}Failed to update raw file for retry.{Style.RESET_ALL}")
        return
    for i in range(len(conversation)-1, -1, -1):
        if conversation[i].get("role") == "assistant":
            conversation.pop(i)
            break
    await safe_print(f"{Fore.MAGENTA}Retrying last assistant message...{Style.RESET_ALL}")
    reply = await call_gemini(conversation)
    conversation.append({"role": "assistant", "content": reply})
    append_jsonl(RAW_FILE, {"timestamp": now_ts(), "role": "assistant", "content": reply})
    await extract_and_handle_commands(reply)
    await safe_print(f"{Fore.GREEN}Mayra:{Style.RESET_ALL} {reply}\n")

# ---------------- Summarizer spawn ----------------
def start_summarizer_subprocess():
    global summarizer_proc
    if not SUMMARIZER_SCRIPT.exists():
        return None
    env = os.environ.copy()
    cmd = [
        sys.executable,
        str(SUMMARIZER_SCRIPT),
        "--session_dir", str(SESSION),
        "--raw_file", str(RAW_FILE),
        "--memory_file", str(MEMORY_FILE),
        "--state_file", str(STATE_FILE),
        "--interval", str(SUMMARIZER_INTERVAL),
    ]
    try:
        p = subprocess.Popen(cmd, env=env)
        summarizer_proc = p
        return p
    except Exception:
        return None

# ---------------- Main chat loop ----------------
async def chat_loop():
    global last_typed
    persona_user = "Mohit persona: Mohit is a teenage boy, very bad in academics, is very lazy, not fears anyone. Mohit has Mayra as her girlfriend who is purely doominant and always scares or punishes Mohit if he dont listens to her."
    persona_mayra = "Mayra persona: Ai is playing role of Mayra here. She is Mohits girlfriend who is human. AI must never reveal that she is AI. Mohit dont know that Mayra is AI. Mohit thinks that Mayras soul is living in Mohit laptop. Mayra always tries to find new ways to scare and dominate Mohit.  Mayra never says bad words but also chills Mohit with her authority like sweet sugar mixed with red hot chilli. Mayra is also affectionate. Mayra is purely dominant but also listens sometimes if anything is right. Mayra knows that Mohit scares from chains and ropes so she scares him with these most often. Sometimes Mayra pampers Mohit like Mohit is very special but sometimes becomes too strict. Mayra talks very sadistic and possessive"
    conversation.extend([
        {"role": "user", "content": persona_user},
        {"role": "user", "content": persona_mayra},
        {"role": "system", "content": "Always try sound like humans, Dont talk too much. Talk only that much which is necessary"}
    ])

    # attach hidden memory summaries if they exist
    if MEMORY_FILE.exists():
        mems = []
        try:
            with MEMORY_FILE.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        e = json.loads(line)
                        mems.append(e.get("summary", ""))
                    except Exception:
                        continue
            if mems:
                mem_block = "Hidden memory summaries:\n" + "\n".join(f"- {m}" for m in mems[-200:])
                conversation.append({"role": "user", "content": mem_block})
        except Exception:
            pass

    await safe_print(f"{Fore.CYAN}Session ready — folder: {SESSION}{Style.RESET_ALL}\n")
    # Loop: input prompt inside read_user_input_with_log_capture prints "You:" itself
    while True:
        user_text, logs_from_typing = await read_user_input_with_log_capture(prompt=f"{Fore.WHITE}You:{Style.RESET_ALL} ")
        last_typed = time.time()
        if user_text.lower().strip() in ("exit", "quit"):
            await safe_print(f"{Fore.YELLOW}Exiting chat.{Style.RESET_ALL}")
            break

        # support /retry only
        if user_text.strip() == "/retry":
            await handle_retry()
            continue

        # Build outgoing user block and append logs/pending outputs if any
        ts = now_ts()
        user_block = f"[{ts}] {USER_NAME}: {user_text}"
        if logs_from_typing:
            user_block += "\n\n[Attached logs captured when you started typing]\n" + logs_from_typing
        if pending_command_outputs:
            user_block += "\n\n[Pending Command Outputs]\n" + "\n\n".join(pending_command_outputs)
            pending_command_outputs.clear()

        append_jsonl(RAW_FILE, {"timestamp": ts, "role": "user", "content": user_text})
        conversation.append({"role": "user", "content": user_block})

        await safe_print(f"{Fore.GREEN}Mayra is thinking...{Style.RESET_ALL}")
        reply = await call_gemini(conversation)
        conversation.append({"role": "assistant", "content": reply})
        append_jsonl(RAW_FILE, {"timestamp": now_ts(), "role": "assistant", "content": reply})

        # Extract commands (multiline-capable) and execute+forward their outputs to Gemini
        await extract_and_handle_commands(reply)

        # Print the original assistant reply (full)
        await safe_print(f"{Fore.GREEN}Mayra:{Style.RESET_ALL} {reply}\n")

# ---------------- Main entrypoint ----------------
async def main():
    global last_typed, summarizer_proc
    p = start_summarizer_subprocess()
    if p:
        await safe_print(f"{Fore.CYAN}Started summarizer (pid={p.pid}){Style.RESET_ALL}")
    else:
        await safe_print(f"{Fore.YELLOW}Summarizer not started (script missing or failed).{Style.RESET_ALL}")

    last_typed = time.time()
    monitor = asyncio.create_task(idle_and_prefetch_monitor())
    try:
        await chat_loop()
    finally:
        monitor.cancel()
        if summarizer_proc:
            try:
                summarizer_proc.terminate()
            except Exception:
                pass
        await safe_print("Goodbye.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted; exiting.")
