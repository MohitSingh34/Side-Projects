#!/usr/bin/env python3
"""
live_api_test_fixed.py
✅ Minimal working test for Gemini Live (BidiGenerateContent)
- Connects via WebSocket
- Sends setup + a user message
- Prints all raw response frames from Gemini
"""

import os
import json
import asyncio
import websockets

API_KEY = os.getenv("GEMINI_API_KEY_msma")
if not API_KEY:
    raise SystemExit("ERROR: GEMINI_API_KEY not set.")

MODEL = "models/gemini-2.0-flash-exp"
WS_URL = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={API_KEY}"

async def test_prompt(prompt: str):
    async with websockets.connect(WS_URL, max_size=10_000_000) as ws:
        print("Connected to Gemini Live API ✅")

        # 1️⃣ Setup phase (official schema — note field names!)
        setup = {
            "setup": {
                "model": MODEL,
                "generation_config": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_output_tokens": 512
                }
            }
        }
        await ws.send(json.dumps(setup))
        print("→ Sent setup")

        # Wait for setupComplete
        while True:
            msg = await ws.recv()
            print("\n[RAW RESPONSE FRAME]", msg)
            j = json.loads(msg)
            if "setup_complete" in j:
                print("✅ Setup complete")
                break

        # 2️⃣ Send the user message
        user_msg = {
            "client_content": {
                "turns": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt}]
                    }
                ],
                "turn_complete": True
            }
        }
        await ws.send(json.dumps(user_msg))
        print("→ Sent user message")

        # 3️⃣ Collect responses
        response_texts = []
        while True:
            msg = await ws.recv()
            print("\n[RAW RESPONSE FRAME]", msg)
            j = json.loads(msg)

            # Collect text parts
            if "server_content" in j:
                for part in j["server_content"].get("parts", []):
                    if "text" in part:
                        response_texts.append(part["text"])

            # Stop when model signals turn complete
            if j.get("server_content", {}).get("turn_complete"):
                break

        print("\n🧠 Gemini Response:\n", "".join(response_texts).strip())

async def main():
    prompt = input("You: ")
    await test_prompt(prompt)

if __name__ == "__main__":
    asyncio.run(main())
