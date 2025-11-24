#!/usr/bin/env python3
"""
Summarizer process (OS-level).
- Reads only new lines from provided raw_file (jsonl).
- Sends the new messages to OpenRouter using OPENROUTER_SUMMARY_KEY (env).
- Asks for a summary <= 60 words, but will accept longer summary — we store whatever model returns.
- Appends summary entry to memory_file (jsonl).
- Keeps memory_file limited to max_entries (50). Deletes oldest if > max_entries.
- Maintains state_file with last processed line index.
"""

import argparse
import asyncio
import aiohttp
import json
import os
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import sys

LOCAL_TZ = ZoneInfo("Asia/Kolkata")
DEFAULT_MODEL = "deepseek/deepseek-r1-0528-qwen3-8b:free"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
MAX_ENTRIES = 50  # memory entry count cap (user requested)
SUMMARY_WORD_TARGET = 60  # request: "up to 60 words", but we store whatever comes back


def now_timestamp():
    return datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")


async def call_openrouter_summary(api_key: str, model: str, messages):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Mayra Summarizer",
    }
    body = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,  # low temp for stable summaries
        "top_p": 0.9,
        "stream": False,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(ENDPOINT, headers=headers, json=body, timeout=120) as resp:
            data = await resp.json()
            try:
                return data["choices"][0]["message"]["content"]
            except Exception:
                return f"[Error parsing summary] {data}"


def read_jsonl_lines(path: Path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    # parse JSON per line
    items = []
    for line in lines:
        try:
            items.append(json.loads(line))
        except Exception:
            # skip broken line
            continue
    return items


def write_jsonl_entry(path: Path, entry: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_state(state_path: Path):
    if not state_path.exists():
        return {"last_index": 0}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {"last_index": 0}


def save_state(state_path: Path, state: dict):
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state), encoding="utf-8")


def enforce_memory_cap(mem_path: Path, max_entries=MAX_ENTRIES):
    items = read_jsonl_lines(mem_path)
    if len(items) <= max_entries:
        return
    # keep newest max_entries
    keep = items[-max_entries:]
    with mem_path.open("w", encoding="utf-8") as f:
        for it in keep:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")


async def summarizer_loop(raw_file: Path, memory_file: Path, state_file: Path, api_key: str, model: str, interval: int):
    # load state
    state = load_state(state_file)
    last_index = state.get("last_index", 0)

    while True:
        try:
            lines = read_jsonl_lines(raw_file)
            total = len(lines)
            # only new messages
            if total > last_index:
                new_msgs = lines[last_index:total]  # list of dicts e.g. {"timestamp","role","content"}
                # build messages for summarization: combine last N messages (or all new ones)
                # We'll send them as user content in a single prompt to the model
                content_to_summarize = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in new_msgs)
                system_msg = {
                    "role": "system",
                    "content": (
                        "You are a summarization assistant. Create a single concise summary of the chat content provided. "
                        f"Try to keep the summary under {SUMMARY_WORD_TARGET} words, but if the content requires more detail, return the full summary. "
                        "Do not invent facts. Keep it coherent and capture important points, tone, and any user preferences expressed."
                    )
                }
                user_msg = {
                    "role": "user",
                    "content": content_to_summarize
                }
                messages = [system_msg, user_msg]
                # call openrouter using the summary key
                summary_api_key = api_key
                summary_result = await call_openrouter_summary(summary_api_key, model, messages)

                # store summary entry
                entry = {
                    "timestamp": now_timestamp(),
                    "from_index": last_index,
                    "to_index": total,
                    "summary": summary_result,
                }
                write_jsonl_entry(memory_file, entry)
                # enforce cap
                enforce_memory_cap(memory_file, MAX_ENTRIES)
                # update last_index state
                last_index = total
                save_state(state_file, {"last_index": last_index})
            # sleep until next cycle
        except Exception as e:
            # log to stderr but keep running
            print(f"[summarizer] error: {e}", file=sys.stderr)
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
        print("[summarizer] WARNING: OPENROUTER_SUMMARY_KEY not set. Exiting.", file=sys.stderr)
        return

    # ensure state file exists
    if not state_file.exists():
        save_state(state_file, {"last_index": 0})

    # run asyncio loop
    try:
        asyncio.run(summarizer_loop(raw_file, memory_file, state_file, api_key, model, interval))
    except KeyboardInterrupt:
        print("[summarizer] interrupted, exiting.")

if __name__ == "__main__":
    main()
