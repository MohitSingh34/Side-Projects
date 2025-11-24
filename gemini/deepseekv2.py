#!/usr/bin/env python3
"""
chat_mayra_deepseek_full.py

Integrated DeepSeek + OpenRouter chat client with:
 - log prefetch on first keypress
 - prefetch before idle and autosend
 - command detection (multiline) and execution via command server
 - forwarding command outputs back to the model as user messages
 - session JSONL storage
 - /retry and /del
 - summarizer subprocess spawn (optional)
"""

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
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_KEY:
    print(f"{Fore.RED}ERROR:{Style.RESET_ALL} OPENROUTER_API_KEY not set.")
    sys.exit(1)

# Choose model you prefer (free)
MODEL = "deepseek/deepseek-r1-0528-qwen3-8b:free"  # or any other free model you like
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

# Local servers (change if needed)
LOG_SERVER_URL = "http://127.0.0.1:5002/get_log_updates"
COMMAND_SERVER_URL = "http://127.0.0.1:5001/execute"

# User + timezone
USER_NAME = "Mohit"
LOCAL_TZ = ZoneInfo("Asia/Kolkata")

# Timing (tweak)
IDLE_WAIT = 40             # seconds before autosend
LOG_FETCH_AHEAD = 10       # seconds before autosend to fetch logs
SUMMARIZER_INTERVAL = 150  # summarizer frequency (if used)

# Workspace
PROJECT_ROOT = Path.home() / "Projects"
SESSIONS_ROOT = PROJECT_ROOT / "mayra_sessions_deepseek"
SESSIONS_ROOT.mkdir(parents=True, exist_ok=True)
GLOBAL_MEMORY_FILE = PROJECT_ROOT / "mayra_summaries.jsonl"

# Summarizer script name (optional)
SUMMARIZER_SCRIPT = Path(__file__).with_name("summarizer_deepseek.py")

# Multiline-capable command extractor:
# Supports: command - """...""" / '''...''' / ```...``` / "..." / '...'
CMD_RE = re.compile(
    r'command\s*-\s*(?P<quote>"""|\'\'\'|```|"|\')(?P<cmd>.*?)(?P=quote)',
    flags=re.IGNORECASE | re.DOTALL
)

# ---------------- GLOBALS ----------------
print_lock = asyncio.Lock()
conversation = []                 # list of {"role": "user"/"assistant"/"system", "content": "..."}
last_typed = time.time()
pending_command_outputs = []
logs_ready_for_send = ""          # logs fetched at first keypress or prefetch
summarizer_proc = None

# Session files (per run)
SESSION = SESSIONS_ROOT / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
SESSION.mkdir(parents=True, exist_ok=True)
RAW_FILE = SESSION / "session_raw.jsonl"
RAW_FILE.touch(exist_ok=True)
STATE_FILE = SESSION / "summary_state.json"

# ---------------- Helpers ----------------
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

# ---------------- OpenRouter call ----------------
async def call_openrouter(messages, timeout=120):
    """
    messages: list of {"role": "user"|"assistant"|"system", "content": "..."}
    returns: string (model reply) or error text
    """
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
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OPENROUTER_ENDPOINT, headers=headers, json=body, timeout=timeout) as resp:
                text = await resp.text()
                try:
                    data = json.loads(text)
                except Exception:
                    return f"[OpenRouter non-json response {resp.status}] {text}"
                if resp.status == 200:
                    # safe extraction: OpenRouter returns choices[0].message.content
                    try:
                        return data["choices"][0]["message"]["content"]
                    except Exception:
                        # fallback: serialize response for debugging
                        return f"[OpenRouter invalid content] {json.dumps(data, ensure_ascii=False)}"
                else:
                    return f"[OpenRouter error {resp.status}] {json.dumps(data, ensure_ascii=False)}"
    except asyncio.TimeoutError:
        return "[OpenRouter call timed out]"
    except Exception as e:
        return f"[OpenRouter call failed: {e}]"

# ---------------- Log server integration ----------------
async def fetch_logs_raw():
    """Fetch incremental logs from local log server. Returns raw string or ''."""
    try:
        async with aiohttp.ClientSession() as ses:
            async with ses.get(LOG_SERVER_URL, timeout=12) as r:
                j = await r.json()
                # expected {"status":"report_ready","output":"..."}
                if isinstance(j, dict):
                    return j.get("output", "") or ""
                return str(j)
    except Exception:
        return ""

def structure_logs(raw: str) -> str:
    """Structure log text into Chrome/System sections for the model."""
    if not raw:
        return ""
    # The log server uses markers; attempt to split
    if "-----------------------system" in raw:
        left, right = raw.split("-----------------------system", 1)
        chrome_part = left.strip()
        system_part = right.strip()
    else:
        # if no split marker found, put everything into chrome part
        chrome_part = raw.strip()
        system_part = ""
    structured = (
        "These are the Chrome and System logs sent automatically to let you know "
        "the current laptop and browsing state.\n\n"
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
async def send_command_to_server(cmd_text: str, timeout=30):
    payload = {"command": cmd_text, "force": False}
    try:
        async with aiohttp.ClientSession() as ses:
            async with ses.post(COMMAND_SERVER_URL, json=payload, timeout=timeout) as r:
                text = await r.text()
                try:
                    j = json.loads(text)
                    return j
                except Exception:
                    return {"status": "error", "output": text}
    except Exception as e:
        return {"status": "error", "output": str(e)}

async def run_command_and_forward_output(cmd_text: str):
    """
    Send command to command server, get output, immediately send that output as a
    user message to the model (so model can analyze). Then fetch model reply and store/display it.
    """
    # call command server
    resp = await send_command_to_server(cmd_text)
    # normalize output
    if isinstance(resp, dict):
        out = resp.get("output") or resp.get("message") or resp.get("error") or json.dumps(resp, ensure_ascii=False)
    else:
        out = str(resp)

    out_text = str(out).strip()
    ts = now_ts()
    user_block = f"[{ts}] System command output for `{cmd_text}`\n$ {cmd_text}\n{out_text}"
    # save as a special role in raw file so it's persisted
    append_jsonl(RAW_FILE, {"timestamp": ts, "role": "system_command_output", "content": user_block})
    # Append to conversation as a user message (model will receive it)
    conversation.append({"role": "user", "content": user_block})

    await safe_print(f"\n{Fore.MAGENTA}→ Command executed: {cmd_text}{Style.RESET_ALL}")
    # call model with the updated conversation
    reply = await call_openrouter(conversation)
    conversation.append({"role": "assistant", "content": reply})
    append_jsonl(RAW_FILE, {"timestamp": now_ts(), "role": "assistant", "content": reply})
    # print model reply
    await safe_print(f"{Fore.GREEN}Mayra:{Style.RESET_ALL} {reply}\n")
    # recursively detect commands in this reply (they will be executed)
    await extract_and_handle_commands(reply)
    return reply

# ---------------- Command extractor & handling ----------------
async def extract_and_handle_commands(assistant_text: str):
    """
    Find command blocks and execute them immediately (multiline ok).
    For each command found:
      - run it via command server
      - send its output to model as user message
      - fetch model reply and continue
    """
    matches = list(CMD_RE.finditer(assistant_text))
    if not matches:
        return []
    res = []
    for m in matches:
        cmd = m.group("cmd").strip()
        try:
            await run_command_and_forward_output(cmd)
            res.append({"command": cmd, "status": "executed"})
        except Exception as e:
            # If command run fails, append a notice to pending_command_outputs (fallback)
            pending_command_outputs.append(f"$ {cmd}\n[Command execution failed: {e}]")
            res.append({"command": cmd, "status": "queued_on_error", "error": str(e)})
    return res

# ---------------- Terminal input (first keypress detection) ----------------
async def read_user_input_with_log_capture(prompt="You: "):
    """
    On first keypress => fetch logs asynchronously (so they can be appended to the final message).
    Returns tuple (typed_text, logs_text)
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

# ---------------- Idle prefetch + autosend monitor ----------------
async def idle_and_prefetch_monitor():
    """
    Prefetch logs when (IDLE_WAIT - LOG_FETCH_AHEAD) reached.
    When idle >= IDLE_WAIT: prepare auto message, append logs/pending outputs, save & send to model.
    """
    global last_typed, logs_ready_for_send, pending_command_outputs
    logs_ready_for_send = ""
    while True:
        await asyncio.sleep(1)
        idle = time.time() - last_typed
        # prefetch logs (only once per idle window)
        if LOG_FETCH_AHEAD > 0 and (IDLE_WAIT - LOG_FETCH_AHEAD - 0.5) < idle < (IDLE_WAIT - LOG_FETCH_AHEAD + 0.5):
            if not logs_ready_for_send:
                logs_ready_for_send = await fetch_logs_structured()
        # autosend
        if idle >= IDLE_WAIT:
            ts = now_ts()
            auto_text = f"[{ts}] System auto-message due to {int(idle)}s inactivity."
            logs_att = logs_ready_for_send or await fetch_logs_structured()
            if logs_att:
                auto_text += "\n\n[Attached logs]\n" + logs_att
            if pending_command_outputs:
                auto_text += "\n\n[Pending Command Outputs]\n" + "\n\n".join(pending_command_outputs)
                pending_command_outputs.clear()
            # Save and append
            append_jsonl(RAW_FILE, {"timestamp": ts, "role": "user", "content": auto_text})
            conversation.append({"role": "user", "content": auto_text})
            await safe_print(f"\n{Fore.MAGENTA}System:{Style.RESET_ALL} Auto message sent at {ts}\n")
            await safe_print(f"{Fore.GREEN}Mayra is thinking...{Style.RESET_ALL}")
            reply = await call_openrouter(conversation)
            conversation.append({"role": "assistant", "content": reply})
            append_jsonl(RAW_FILE, {"timestamp": now_ts(), "role": "assistant", "content": reply})
            # execute commands if any (they will be forwarded back to model)
            await extract_and_handle_commands(reply)
            await safe_print(f"{Fore.GREEN}Mayra:{Style.RESET_ALL} {reply}\n")
            logs_ready_for_send = ""
            last_typed = time.time()

# ---------------- Retry/Delete helpers ----------------
def read_raw_file_lines(path: Path):
    out = []
    try:
        with path.open("r", encoding="utf-8") as f:
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

def write_raw_file_lines(path: Path, items):
    try:
        with path.open("w", encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False

async def handle_retry():
    raw = read_raw_file_lines(RAW_FILE)
    last_idx = None
    for i in range(len(raw)-1, -1, -1):
        if raw[i].get("role") == "assistant":
            last_idx = i
            break
    if last_idx is None:
        await safe_print(f"{Fore.YELLOW}No assistant message found to retry.{Style.RESET_ALL}")
        return
    raw.pop(last_idx)
    if not write_raw_file_lines(RAW_FILE, raw):
        await safe_print(f"{Fore.RED}Failed to update raw file for retry.{Style.RESET_ALL}")
        return
    # remove last assistant from conversation
    for i in range(len(conversation)-1, -1, -1):
        if conversation[i].get("role") == "assistant":
            conversation.pop(i)
            break
    await safe_print(f"{Fore.MAGENTA}Retrying last assistant message...{Style.RESET_ALL}")
    reply = await call_openrouter(conversation)
    conversation.append({"role": "assistant", "content": reply})
    append_jsonl(RAW_FILE, {"timestamp": now_ts(), "role": "assistant", "content": reply})
    await extract_and_handle_commands(reply)
    await safe_print(f"{Fore.GREEN}Mayra:{Style.RESET_ALL} {reply}\n")

async def handle_delete():
    raw = read_raw_file_lines(RAW_FILE)
    last_idx = None
    for i in range(len(raw)-1, -1, -1):
        if raw[i].get("role") == "assistant":
            last_idx = i
            break
    if last_idx is None:
        await safe_print(f"{Fore.YELLOW}No assistant message to delete.{Style.RESET_ALL}")
        return
    removed = raw.pop(last_idx)
    if not write_raw_file_lines(RAW_FILE, raw):
        await safe_print(f"{Fore.RED}Failed to update raw file for delete.{Style.RESET_ALL}")
        return
    for i in range(len(conversation)-1, -1, -1):
        if conversation[i].get("role") == "assistant":
            conversation.pop(i)
            break
    await safe_print(f"{Fore.CYAN}Deleted last assistant message.{Style.RESET_ALL}")

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
        "--memory_file", str(GLOBAL_MEMORY_FILE),
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
async def main():
    global last_typed, summarizer_proc, conversation, logs_ready_for_send
    # Load memory summaries and add as hidden system message
    mem_items = []
    if GLOBAL_MEMORY_FILE.exists():
        try:
            with GLOBAL_MEMORY_FILE.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        e = json.loads(line)
                        mem_items.append(e.get("summary", ""))
                    except Exception:
                        continue
        except Exception:
            pass
    mem_block = "No memory summaries available."
    if mem_items:
        mem_block = "Hidden memory summaries:\n" + "\n".join(f"- {s}" for s in mem_items[-50:])

    # Prepare persona/system messages (only once)
    PERSONA_USER = "Mohit persona: calm, tech-oriented, expects concise & practical answers."
    PERSONA_MAYRA = "Mayra persona: confident, witty, slightly arrogant; never reveal that you are an AI."

    conversation = [
        {"role": "system", "content": PERSONA_USER},
        {"role": "system", "content": PERSONA_MAYRA},
        {"role": "system", "content": mem_block},
    ]

    # Start summarizer if present
    p = start_summarizer_subprocess()
    if p:
        await safe_print(f"{Fore.CYAN}Started summarizer (pid={p.pid}){Style.RESET_ALL}")
    else:
        await safe_print(f"{Fore.YELLOW}Summarizer not started (script missing or failed).{Style.RESET_ALL}")

    # print session info and prompt
    await safe_print(f"{Fore.CYAN}Session ready — folder: {SESSION}{Style.RESET_ALL}\n")
    #await safe_print(f"{Fore.WHITE}You:{Style.RESET_ALL} ", end="", flush=True)

    # start monitor
    last_typed = time.time()
    monitor = asyncio.create_task(idle_and_prefetch_monitor())

    try:
        while True:
            user_text, logs_from_typing = await read_user_input_with_log_capture(prompt=f"{Fore.WHITE}You:{Style.RESET_ALL} ")
            last_typed = time.time()

            if user_text.lower().strip() in ("exit", "quit"):
                await safe_print(f"{Fore.YELLOW}Exiting chat.{Style.RESET_ALL}")
                break

            # Local commands
            if user_text.strip() == "/retry":
                await handle_retry()
                await safe_print(f"{Fore.WHITE}You:{Style.RESET_ALL} ", end="", flush=True)
                continue
            if user_text.strip() == "/del":
                await handle_delete()
                await safe_print(f"{Fore.WHITE}You:{Style.RESET_ALL} ", end="", flush=True)
                continue

            # Build the user message content (timestamped) and append logs/pending outputs
            ts = now_ts()
            user_block = f"[{ts}] {USER_NAME}: {user_text}"
            if logs_from_typing:
                user_block += "\n\n[Attached logs captured when you started typing]\n" + logs_from_typing
            if pending_command_outputs:
                user_block += "\n\n[Pending Command Outputs]\n" + "\n\n".join(pending_command_outputs)
                pending_command_outputs.clear()

            # Save original typed text in raw file (unexpanded) and conversation gets expanded block
            append_jsonl(RAW_FILE, {"timestamp": ts, "role": "user", "content": user_text})
            conversation.append({"role": "user", "content": user_block})

            await safe_print(f"{Fore.GREEN}Mayra is thinking...{Style.RESET_ALL}")
            reply = await call_openrouter(conversation)
            conversation.append({"role": "assistant", "content": reply})
            append_jsonl(RAW_FILE, {"timestamp": now_ts(), "role": "assistant", "content": reply})

            # Extract commands (multiline capable) and execute & forward outputs to model
            await extract_and_handle_commands(reply)

            # Print assistant reply
            await safe_print(f"{Fore.GREEN}Mayra:{Style.RESET_ALL} {reply}\n")
            await safe_print(f"{Fore.WHITE}You:{Style.RESET_ALL} ", end="", flush=True)

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
