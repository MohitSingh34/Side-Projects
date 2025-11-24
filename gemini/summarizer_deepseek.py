#!/usr/bin/env python3
"""
summarizer_process.py

OS-level summarizer. Reads only new lines from session_raw.jsonl and creates
human-friendly, chain-aware summaries using OpenRouter (DeepSeek). Handles retries
for failed batches (e.g., 429 rate limits) and stores summaries in a global memory file.

Usage (spawned from main chat):
python3 summarizer_process.py --session_dir <dir> --raw_file <path> --memory_file <path> --state_file <path> --interval 150 --model deepseek/deepseek-r1-0528-qwen3-8b:free
"""

import argparse
import asyncio
import aiohttp
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Asia/Kolkata")
DEFAULT_MODEL = "deepseek/deepseek-r1-0528-qwen3-8b:free"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

MAX_ENTRIES = 50            # keep last 50 summary entries
SUMMARY_WORD_TARGET = 60    # request target (we still store whatever model returns)


def now_timestamp():
    return datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")


# ---------------- JSONL helpers ----------------
def read_jsonl(path: Path):
    if not path.exists():
        return []
    items = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                # skip malformed lines
                continue
    return items


def append_jsonl(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def overwrite_jsonl(path: Path, items: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")


# ---------------- state helpers ----------------
def load_state(state_path: Path):
    if not state_path.exists():
        return {"last_index": 0, "pending": []}  # pending: list of {"from":, "to":}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {"last_index": 0, "pending": []}


def save_state(state_path: Path, state: dict):
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    os.replace(str(tmp), str(state_path))


def enforce_memory_cap(mem_path: Path, max_entries=MAX_ENTRIES):
    items = read_jsonl(mem_path)
    if len(items) <= max_entries:
        return
    keep = items[-max_entries:]
    overwrite_jsonl(mem_path, keep)


# ---------------- OpenRouter summarization call ----------------
async def call_openrouter(api_key: str, model: str, messages: list, timeout=120):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Mayra Summarizer",
    }
    body = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "top_p": 0.9,
        "stream": False,
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(ENDPOINT, json=body, headers=headers, timeout=timeout) as resp:
                text = await resp.text()
                # try parse JSON
                try:
                    data = json.loads(text)
                except Exception:
                    return False, f"[Non-json response {resp.status}] {text}"

                # success path
                if resp.status == 200:
                    try:
                        content = data["choices"][0]["message"]["content"]
                        return True, content
                    except Exception:
                        return False, f"[Parsing error] {data}"
                else:
                    # return error info for retry logic
                    return False, {"status": resp.status, "body": data}
        except asyncio.TimeoutError:
            return False, {"status": "timeout", "body": "timeout"}
        except Exception as e:
            return False, {"status": "network_error", "body": str(e)}


# ---------------- build a better summarization prompt ----------------
def build_summary_prompt(new_msgs: list, memory_summaries: list):
    """
    new_msgs: list of dicts with keys timestamp, role, content
    memory_summaries: list of existing summaries (dicts)
    """
    # Make memory text concise but present
    mem_text = ""
    if memory_summaries:
        mem_text = "Long-term memory summaries (most recent first):\n"
        for i, s in enumerate(reversed(memory_summaries[-10:])):  # send only last 10 summaries to keep prompt size reasonable
            summary_text = s.get("summary") if isinstance(s, dict) else str(s)
            mem_text += f"{i+1}. {summary_text}\n"

    # Build chat text with labels and timestamps
    chat_text = []
    for m in new_msgs:
        ts = m.get("timestamp") or m.get("datetime") or now_timestamp()
        role = (m.get("role") or "user").upper()
        content = m.get("content") or m.get("text") or ""
        chat_text.append(f"[{ts}] {role}: {content}")

    # Strong system instruction: chain-aware, coherent, human-friendly, connect with memory
    system_prompt = ("You are a professional summarizer. keep in mind that our main of summarisation is giving local ai memory, these summaries will be used as entry in a jsonl file."
              " Aim for around 60 words. "
              "if chats contain any command then in memory clearly write how it got used during conversation."
              "Be concise, factual, and coherent"
    )

    # user content packing both memory and messages
    user_content = "Chat messages to summarize:\n\n"
    if mem_text:
        user_content += mem_text + "\n"
    user_content += "\n".join(chat_text)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    return messages


# ---------------- main summarizer loop ----------------
async def summarizer_loop(raw_file: Path, memory_file: Path, state_file: Path, api_key: str, model: str, interval: int):
    state = load_state(state_file)
    last_index = int(state.get("last_index", 0))
    pending = state.get("pending", [])  # list of {"from": int, "to": int}

    while True:
        try:
            all_msgs = read_jsonl(raw_file)
            total = len(all_msgs)

            # First, reattempt pending batches (from previous failures) before new ones
            if pending:
                new_pending = []
                for batch in pending:
                    f = int(batch["from"])
                    t = int(batch["to"])
                    # safe clamp
                    if f < 0 or f >= len(all_msgs):
                        continue
                    t = min(t, len(all_msgs))
                    new_msgs = all_msgs[f:t]
                    memory = read_jsonl(memory_file)
                    messages = build_summary_prompt(new_msgs, memory)
                    ok, res = await call_openrouter(api_key, model, messages)
                    if ok:
                        entry = {"timestamp": now_timestamp(), "from_index": f, "to_index": t, "summary": res}
                        append_jsonl(memory_file, entry)
                        enforce_memory_cap(memory_file, MAX_ENTRIES)
                        last_index = max(last_index, t)
                    else:
                        # keep for next cycle
                        new_pending.append({"from": f, "to": t, "error": res})
                pending = new_pending
                state.update({"last_index": last_index, "pending": pending})
                save_state(state_file, state)

            # Now handle new messages (if any)
            if total > last_index:
                f = last_index
                t = total
                new_msgs = all_msgs[f:t]
                # build prompt including long-term memory snippet
                memory = read_jsonl(memory_file)
                messages = build_summary_prompt(new_msgs, memory)
                ok, res = await call_openrouter(api_key, model, messages)
                if ok:
                    entry = {"timestamp": now_timestamp(), "from_index": f, "to_index": t, "summary": res}
                    append_jsonl(memory_file, entry)
                    enforce_memory_cap(memory_file, MAX_ENTRIES)
                    last_index = t
                    state.update({"last_index": last_index, "pending": pending})
                    save_state(state_file, state)
                else:
                    # on failure, push this range to pending, store minimal failure note in state
                    pending.append({"from": f, "to": t, "error": res})
                    state.update({"last_index": last_index, "pending": pending})
                    save_state(state_file, state)
            # sleep before next cycle
        except Exception as e:
            print(f"[summarizer] loop error: {e}", file=sys.stderr)
        await asyncio.sleep(interval)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--session_dir", required=True)
    p.add_argument("--raw_file", required=True)
    p.add_argument("--memory_file", required=True)
    p.add_argument("--state_file", required=True)
    p.add_argument("--interval", default="150")
    p.add_argument("--model", default=DEFAULT_MODEL)
    return p.parse_args()


def main():
    args = parse_args()
    raw_file = Path(args.raw_file)
    memory_file = Path(args.memory_file)
    state_file = Path(args.state_file)
    interval = int(args.interval)
    model = args.model
    api_key = os.getenv("OPENROUTER_SUMMARY_KEY", "")

    if not api_key:
        print("[summarizer] ERROR: OPENROUTER_SUMMARY_KEY not set. Exiting.", file=sys.stderr)
        sys.exit(1)

    if not state_file.exists():
        save_state(state_file, {"last_index": 0, "pending": []})

    try:
        asyncio.run(summarizer_loop(raw_file, memory_file, state_file, api_key, model, interval))
    except KeyboardInterrupt:
        print("[summarizer] interrupted, exiting.")


if __name__ == "__main__":
    main()
