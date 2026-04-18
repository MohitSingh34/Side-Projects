#!/usr/bin/env python3
"""
AI Scraper Worker Node - Microservice for individual AI agents
Usage: python ai_scraper_worker.py --model deepseek --port 8001 --profile /path/to/chrome/profile
"""

import json
import time
import os
import asyncio
import uvicorn
import uuid
import re
import base64
import tempfile
import requests
import argparse
import sys
from typing import List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from datetime import datetime
import subprocess
import psutil

Parse command line arguments

parser = argparse.ArgumentParser(description='AI Scraper Worker Node')
parser.add_argument('--model', type=str, required=True, help='Model type: chatgpt, deepseek, or gemini')
parser.add_argument('--port', type=int, default=8000, help='Port number to run FastAPI server on')
parser.add_argument('--profile', type=str, help='Chrome profile directory path')
args = parser.parse_args()

Worker configuration

WORKER_MODEL = args.model
WORKER_PORT = args.port
CHROME_PROFILE = args.profile if args.profile else f"/home/mohit/chrome-profile-{WORKER_MODEL}-{WORKER_PORT}"

print(f"🚀 WORKER MODE: Model={WORKER_MODEL}, Port={WORKER_PORT}, Profile={CHROME_PROFILE}")

Task board directory for inter-process communication

TASK_BOARD_DIR = "/home/mohit/Side-Projects/Selenium/task_board"
os.makedirs(TASK_BOARD_DIR, exist_ok=True)

Global variables

driver = None
action_lock = asyncio.Lock()
worker_window = None

def save_task_completion(response_text: str):
"""Save completed task to task board for orchestrator to read"""
timestamp = int(time.time())
task_file = os.path.join(TASK_BOARD_DIR, f"task_{WORKER_MODEL}{WORKER_PORT}{timestamp}.txt")
try:
with open(task_file, "w", encoding="utf-8") as f:
f.write(response_text)
print(f"📋 Task completion saved: {task_file}")
return task_file
except Exception as e:
print(f"⚠️ Failed to save task: {e}")
return None

def copy_text_to_clipboard(text: str):
subprocess.run(['xclip', '-selection', 'clipboard'], input=text.encode('utf-8'), check=True)

def init_driver():
global driver, worker_window
if driver is None:
print(f"🚀 Starting Chrome with profile: {CHROME_PROFILE}")
options = uc.ChromeOptions()
options.add_argument(f"--user-data-dir={CHROME_PROFILE}")

driver = uc.Chrome(
options=options,
driver_executable_path="/home/mohit/.cache/selenium/chromedriver/linux64/146.0.7680.153/chromedriver",
version_main=146,
)
time.sleep(3)

Open the appropriate AI website

driver.switch_to.new_window("tab")
worker_window = driver.current_window_handle

if WORKER_MODEL == "deepseek":
driver.get("https://chat.deepseek.com/")
elif WORKER_MODEL == "gemini":
driver.get("https://gemini.google.com/app")
else: # chatgpt
driver.get("https://chatgpt.com/")

print(f"✅ Worker ({WORKER_MODEL}) loaded!")
time.sleep(3)

----------------- Worker Logic (Simplified - Single Agent) -----------------

async def send_and_extract(prompt_text: str, files: Optional[List[str]] = None):
"""Generic send and extract for the worker's assigned model"""
async with action_lock:
driver.switch_to.window(worker_window)
await asyncio.sleep(1)

if WORKER_MODEL == "deepseek":
return await extract_deepseek(prompt_text, files)
elif WORKER_MODEL == "gemini":
return await extract_gemini(prompt_text, files)
else: # chatgpt
return await extract_chatgpt(prompt_text, files)

async def extract_chatgpt(prompt_text: str, files: Optional[List[str]] = None):
text_area = driver.find_element(By.CSS_SELECTOR, "div#prompt-textarea")
text_area.send_keys(Keys.CONTROL + "a")
text_area.send_keys(Keys.BACKSPACE)
await asyncio.sleep(0.5)

if prompt_text:
copy_text_to_clipboard(prompt_text)
text_area.send_keys(Keys.CONTROL, "v")

send_btn = driver.find_element(By.CSS_SELECTOR, "button[data-testid='send-button']")
send_btn.click()
await asyncio.sleep(15) # Wait for response

messages = driver.find_elements(By.CSS_SELECTOR, "div[data-message-author-role='assistant']")
if messages:
return {"formatted_markdown": messages[-1].text}
return {"formatted_markdown": "Error: No response"}

async def extract_deepseek(prompt_text: str, files: Optional[List[str]] = None):
text_area = driver.find_element(By.CSS_SELECTOR, "textarea[placeholder='Message DeepSeek']")
text_area.send_keys(Keys.CONTROL + "a")
text_area.send_keys(Keys.BACKSPACE)
await asyncio.sleep(0.5)

if prompt_text:
copy_text_to_clipboard(prompt_text)
text_area.send_keys(Keys.CONTROL, "v")

text_area.send_keys(Keys.ENTER)
await asyncio.sleep(15)

messages = driver.find_elements(By.CSS_SELECTOR, "div._4f9bf79")
if messages:
return {"formatted_markdown": messages[-1].text}
return {"formatted_markdown": "Error: No response"}

async def extract_gemini(prompt_text: str, files: Optional[List[str]] = None):
text_area = driver.find_element(By.CSS_SELECTOR, "div.ql-editor[contenteditable='true']")
text_area.send_keys(Keys.CONTROL + "a")
text_area.send_keys(Keys.BACKSPACE)
await asyncio.sleep(0.5)

if prompt_text:
copy_text_to_clipboard(prompt_text)
text_area.send_keys(Keys.CONTROL, "v")

send_btn = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Send message']")
send_btn.click()
await asyncio.sleep(15)

copy_buttons = driver.find_elements(By.CSS_SELECTOR, "button[data-test-id='copy-button']")
if copy_buttons:
copy_buttons[-1].click()
await asyncio.sleep(1)
result = subprocess.run(['xclip', '-selection', 'clipboard', '-o'], capture_output=True, text=True)
return {"formatted_markdown": result.stdout}
return {"formatted_markdown": "Error: No response"}

----------------- FastAPI Server -----------------

@asynccontextmanager
async def lifespan(app: FastAPI):
init_driver()
yield
if driver:
driver.quit()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
CORSMiddleware,
allow_origins=[""],
allow_credentials=True,
allow_methods=[""],
allow_headers=["*"],
)

class ChatMessage(BaseModel):
role: str
content: str

class ChatCompletionRequest(BaseModel):
model: str
messages: List[ChatMessage]
files: Optional[List[str]] = None
stream: Optional[bool] = False
model_config = ConfigDict(extra="allow")

@app.get("/health")
async def health():
return {"status": "healthy", "model": WORKER_MODEL, "port": WORKER_PORT}

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
try:

Extract prompt from messages

prompt = req.messages[-1].content if req.messages else ""

print(f"📨 Worker {WORKER_MODEL}:{WORKER_PORT} received task")

Process the request

result = await send_and_extract(prompt, req.files)
md_text = result.get("formatted_markdown", "")

Save to task board for async reading

save_task_completion(md_text)

return {
"id": f"chatcmpl-{uuid.uuid4().hex}",
"object": "chat.completion",
"created": int(time.time()),
"model": req.model,
"choices": [{
"index": 0,
"message": {"role": "assistant", "content": md_text},
"finish_reason": "stop"
}]
}
except Exception as e:
raise HTTPException(status_code=500, detail=str(e))

if name == "main":
print(f"🌐 Starting {WORKER_MODEL} worker on port {WORKER_PORT}")
uvicorn.run(app, host="0.0.0.0", port=WORKER_PORT, reload=False)