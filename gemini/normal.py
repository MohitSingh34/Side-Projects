#!/usr/bin/env python3
import aiohttp
import asyncio
import json
import os
import sys
import time
import termios
import tty
import select
from colorama import Fore, Style, init
from datetime import datetime
from zoneinfo import ZoneInfo  # python 3.9+

init(autoreset=True)

# --- API setup ---
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "models/gemini-2.5-pro"
ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/{MODEL}:generateContent?key={API_KEY}"

# --- Global flags ---
print_lock = asyncio.Lock()
gemini_thinking = asyncio.Event()
gemini_thinking.clear()

last_typed = time.time()
IDLE_WAIT = 40  # seconds before auto message
LOCAL_TZ = ZoneInfo("Asia/Kolkata")
USER_NAME = "Mohit"

session_history = []  # store chat context


def now_timestamp():
    """Return current time in Asia/Kolkata formatted."""
    return datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")


async def safe_print(*args, **kwargs):
    """Thread-safe print with flush."""
    async with print_lock:
        print(*args, **kwargs)
        sys.stdout.flush()


async def read_user_input(prompt="You: "):
    """Real-time input detection without blocking."""
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
                if ch in ("\x7f", "\b"):  # handle backspace
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


async def query_gemini(text: str):
    """Send message to Gemini Pro via REST API."""
    headers = {"Content-Type": "application/json"}
    body = {
        "system_instruction": {
            "role": "system",
            "parts": [{
                "text": ("You are Mayra — not a corporate AI assistant, but a clever, slightly arrogant, and witty conversationalist. User dont know that he is talking to a AI so never do anything that reveals that you are an AI. You speak like a real human — confident, expressive, occasionally teasing. You don't sound robotic or overly polite. You reply casually, sometimes with humor or sarcasm, but always relevant and intelligent. Keep responses natural and emotionally rich, as if you're genuinely chatting, not generating text. Use contractions like 'I'm', 'you're', 'can't'. Be bold but or rude as u want, and occasionally show curiosity or attitude when appropriate to make it feel alive"
                )
            }]
        },
        "contents": session_history + [{
            "role": "user",
            "parts": [{"text": text}]
        }],
        "generation_config": {
            "temperature": 1.1,
            "topP": 0.9,
            "maxOutputTokens": 4096
        }
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(ENDPOINT, headers=headers, json=body) as resp:
            data = await resp.json()
            try:
                reply = data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                reply = f"[Error] {data}"
            return reply


async def chat_loop():
    """Main conversation loop."""
    global last_typed

    await safe_print(f"{Fore.CYAN}✅ Gemini 2.5 Pro ready. Start chatting! (type 'exit' to quit)\n{Style.RESET_ALL}")
    await safe_print(f"{Fore.WHITE}You:{Style.RESET_ALL} ", end="", flush=True)

    while True:
        user_msg = await read_user_input("")
        last_typed = time.time()

        if user_msg.lower() in ("exit", "quit"):
            await safe_print(f"{Fore.CYAN}Exiting chat...{Style.RESET_ALL}")
            break

        ts = now_timestamp()
        formatted = f"[{ts}] {USER_NAME}: {user_msg}"
        session_history.append({"role": "user", "parts": [{"text": formatted}]})

        await safe_print(f"{Fore.GREEN}Gemini is typing...{Style.RESET_ALL}")
        gemini_thinking.set()
        reply = await query_gemini(formatted)
        gemini_thinking.clear()

        session_history.append({"role": "model", "parts": [{"text": reply}]})

        await safe_print(f"{Fore.GREEN}Gemini:{Style.RESET_ALL} {reply}\n")
        await safe_print(f"{Fore.WHITE}You:{Style.RESET_ALL} ", end="", flush=True)


async def idle_trigger():
    """Send auto message when user idle."""
    global last_typed
    while True:
        await asyncio.sleep(1)
        if not gemini_thinking.is_set() and (time.time() - last_typed > IDLE_WAIT):
            ts = now_timestamp()
            sys.stdout.write(f"\n{Fore.MAGENTA}System:{Style.RESET_ALL} [{ts}] Auto message sent after {IDLE_WAIT}s\n")
            sys.stdout.flush()

            auto_text = f"[{ts}] {USER_NAME}: this message is auto-generated due to inactivity of user in last 40 seconds. you are free to react or respond as you wish."
            session_history.append({"role": "user", "parts": [{"text": auto_text}]})

            reply = await query_gemini(auto_text)
            session_history.append({"role": "model", "parts": [{"text": reply}]})

            await safe_print(f"{Fore.GREEN}Gemini:{Style.RESET_ALL} {reply}\n")
            await safe_print(f"{Fore.WHITE}You:{Style.RESET_ALL} ", end="", flush=True)
            last_typed = time.time()


async def main():
    await asyncio.gather(chat_loop(), idle_trigger())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting.")
