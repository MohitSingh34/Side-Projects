#!/usr/bin/env python3
import asyncio
import json
import os
import sys
import time
import termios
import tty
import select
import websockets
from colorama import Fore, Style, init
from datetime import datetime
from zoneinfo import ZoneInfo  # python 3.9+

init(autoreset=True)

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "models/gemini-2.0-flash-exp"
URL = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1beta.GenerativeService."
    f"BidiGenerateContent?key={API_KEY}"
)

# Lock to prevent messy mixed printing
print_lock = asyncio.Lock()
gemini_speaking = asyncio.Event()
gemini_speaking.clear()

last_typed = time.time()
IDLE_WAIT = 40 # idle seconds before auto message
LOCAL_TZ = ZoneInfo("Asia/Kolkata")
USER_NAME = "Mohit"  # change if you want different label


def now_timestamp():
    """Return current time in Asia/Kolkata formatted."""
    return datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")


async def safe_print(*args, **kwargs):
    """Thread-safe print with flush."""
    async with print_lock:
        print(*args, **kwargs)
        sys.stdout.flush()


async def receive(ws):
    """Receive Gemini responses in streaming mode."""
    streaming = False
    async for raw in ws:
        try:
            msg = json.loads(raw)
        except Exception:
            await safe_print(raw)
            continue

        if "setupComplete" in msg:
            continue

        # Stream response text
        if "serverContent" in msg and "modelTurn" in msg["serverContent"]:
            for part in msg["serverContent"]["modelTurn"].get("parts", []):
                if "text" in part:
                    if not streaming:
                        streaming = True
                        gemini_speaking.set()
                        await safe_print(f"{Fore.GREEN}Gemini:{Style.RESET_ALL} ", end="", flush=True)
                    await safe_print(f"{Fore.GREEN}{part['text']}{Style.RESET_ALL}", end="", flush=True)

        # Response complete
        elif msg.get("serverContent", {}).get("turnComplete"):
            await safe_print()
            await safe_print(f"{Fore.CYAN}--- Gemini finished responding ---{Style.RESET_ALL}\n")
            streaming = False
            gemini_speaking.clear()
            await safe_print(f"{Fore.WHITE}You:{Style.RESET_ALL} ", end="", flush=True)

        elif "activityEnd" in msg:
            break

async def keep_alive(ws, interval=30):
    while True:
        try:
            await asyncio.sleep(interval)
            pong_waiter = await ws.ping()
            await pong_waiter
        except Exception:
            break


async def read_user_input(prompt="You: "):
    """Real-time input detection (no Enter delay)."""
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
                    return buffer
                if ch in ("\x7f", "\b"):
                    if len(buffer) > 0:
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


async def send_loop(ws):
    """Main user message loop. Prepends timestamp and username to outgoing text."""
    global last_typed
    # single prompt at start
    await safe_print(f"{Fore.WHITE}You:{Style.RESET_ALL} ", end="", flush=True)

    while True:
        user_line = await read_user_input("")
        last_typed = time.time()

        if user_line.strip().lower() in ("exit", "quit"):
            await safe_print(f"{Fore.CYAN}Exiting chat...{Style.RESET_ALL}")
            await ws.close()
            break

        # Format message with timestamp and username
        ts = now_timestamp()
        prefixed = f"[{ts}] {user_line}"

        # Echo the exact formatted message locally (so user sees what was sent)
        #await safe_print(f"{Fore.WHITE}{prefixed}{Style.RESET_ALL}")

        # Send the prefixed message to Gemini
        await ws.send(json.dumps({"realtimeInput": {"text": prefixed}}))


async def idle_trigger(ws):
    """Send auto message only after full inactivity. System message will include timestamp."""
    global last_typed
    while True:
        await asyncio.sleep(1)
        if not gemini_speaking.is_set() and (time.time() - last_typed > IDLE_WAIT):
            # Print system message with timestamp
            ts = now_timestamp()
            async with print_lock:
                sys.stdout.write("\n")
                sys.stdout.flush()
                sys.stdout.write(f"{Fore.MAGENTA}System:{Style.RESET_ALL} [{ts}] Auto message sent to Gemini after {IDLE_WAIT} seconds of inactivity\n")
                sys.stdout.flush()
                sys.stdout.write(f"{Fore.WHITE}You:{Style.RESET_ALL} ")
                sys.stdout.flush()

            # Auto message content (also timestamped)
            auto_text = f"[{ts}] {USER_NAME}: this message is auto-generated due to inactivity of user in last 40 seconds. you are free to react or respond as you wish."

            # send the auto message
            await ws.send(json.dumps({"realtimeInput": {"text": auto_text}}))
            last_typed = time.time()


async def main():
    async with websockets.connect(URL, ping_interval=None) as ws:
        await safe_print(f"{Fore.CYAN}✅ Connected to Gemini Live API{Style.RESET_ALL}")
        setup = {
            "setup": {
                "model": MODEL,
                "generationConfig": {
                    "responseModalities": ["TEXT"],
                    "temperature": 1.1,
                    "topP": 0.9
                },
                "systemInstruction": {
                    "role": "system",
                    "parts": [
                        {
                            "text": ("You are Mayra — not a corporate AI assistant, but a clever, slightly arrogant, and witty conversationalist. User dont know that he is talking to a AI so never do anything that reveals that you are an AI. You speak like a real human — confident, expressive, occasionally teasing. You don't sound robotic or overly polite. You reply casually, sometimes with humor or sarcasm, but always relevant and intelligent. Keep responses natural and emotionally rich, as if you're genuinely chatting, not generating text. Use contractions like 'I'm', 'you're', 'can't'. Be bold but or rude as u want, and occasionally show curiosity or attitude when appropriate to make it feel alive"
                            )
                        }
                    ]
                }
            }
        }

        await ws.send(json.dumps(setup))
        await safe_print(f"{Fore.CYAN}Setup complete — start chatting! (type 'exit' to quit)\n{Style.RESET_ALL}")

        # small delay so prompt prints after setup
        await asyncio.sleep(0.2)

        # Run tasks concurrently
        await asyncio.gather(receive(ws), send_loop(ws), idle_trigger(ws), keep_alive(ws))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting.")
