import json
import time
import os
import asyncio
import uvicorn
import uuid
from typing import List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys  # ✨ NAYA IMPORT React Hack ke liye
from datetime import datetime

# Core Paths
NOTES_DIR = "/home/mohit/Projects/notes"
PENDING_JSON_PATH = os.path.join(NOTES_DIR, "pending_chatgpt.json")

# Global variables
driver = None
driver_lock = asyncio.Lock()

def init_driver():
    global driver
    if driver is None:
        print("Starting undetected chromedriver... (taking it easy for i3)")
        options = uc.ChromeOptions()
        options.add_argument("--user-data-dir=/home/mohit/chrome-profile-ucc")

        driver = uc.Chrome(options=options)
        driver.get("https://chatgpt.com/")
        print("Profile loaded! Server is ready.")
        time.sleep(5)

async def wait_for_response_to_complete():
    await asyncio.sleep(3)
    max_wait = 120
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            # Check for voice button (means it's idle and ready)
            voice_btn = driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Start Voice']")
            if voice_btn:
                await asyncio.sleep(2)
                return True

            # Check for send button being re-enabled
            send_btn = driver.find_elements(By.CSS_SELECTOR, "button[data-testid='send-button']")
            if send_btn and not send_btn[0].get_attribute("disabled"):
                await asyncio.sleep(2)
                return True
        except Exception:
            pass
        await asyncio.sleep(2)
    return False

async def send_and_extract(prompt_text: str, files: Optional[List[str]] = None):
    """Core function to safely send a prompt and extract the output IN PERFECT ORDER"""
    # Halki si saans lene do script ko
    await asyncio.sleep(1)

    # --- ✨ NEW: File Upload Logic ---
    if files:
        try:
            # Pata nai kitne input[type=file] hain, but pehla wala is usually for composer
            file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
            for file_path in files:
                if os.path.exists(file_path):
                    # Direct send_keys bypassing OS window
                    file_input.send_keys(file_path)
                    print(f"Uploading file: {file_path}")
                    await asyncio.sleep(1) # Chhota pause between files
                else:
                    print(f"File not found, skipping: {file_path}")
            
            # Wait for all files to finish uploading by checking for 'Remove file' buttons
            print(f"Waiting for {len(files)} files to complete uploading...")
            max_wait = 60
            start = time.time()
            while time.time() - start < max_wait:
                remove_btns = driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Remove file']")
                if len(remove_btns) >= len(files):
                    print("All files seemingly uploaded!")
                    break
                await asyncio.sleep(1)
            # Extra buffer just in case UI lag is there
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Error during file upload: {e}")

    # Seedha element pakdo bina WebDriverWait ke nakhro ke
    text_area = driver.find_element(By.CSS_SELECTOR, "div#prompt-textarea")
    driver.execute_script("arguments[0].scrollIntoView();", text_area)
    await asyncio.sleep(0.5)
    driver.execute_script("arguments[0].click();", text_area)
    # Clear reliably for contenteditable
    text_area.send_keys(Keys.CONTROL + "a")
    text_area.send_keys(Keys.BACKSPACE)

    # 1. Text type karo (Newline handle karne ke liye Shift+Enter)
    lines = prompt_text.split('\n')
    for i, line in enumerate(lines):
        text_area.send_keys(line)
        if i < len(lines) - 1:
            text_area.send_keys(Keys.SHIFT + Keys.ENTER)


    # ✨ 2. Tumhare hisaab se exact 1.3 seconds ka wait
    await asyncio.sleep(1.3)

    # ✨ 3. Button click chhoro, direct ENTER maaro!
    text_area.send_keys(Keys.ENTER)

    is_done = await wait_for_response_to_complete()
    if not is_done:
        raise Exception("Response generation timed out.")

    messages = driver.find_elements(By.CSS_SELECTOR, "div[data-message-author-role='assistant']")
    latest_message = messages[-1]

    formatted_markdown = ""
    plain_text_parts = []
    code_blocks = {}

    elements = latest_message.find_elements(By.CSS_SELECTOR, "div.markdown.prose > *")

    code_idx = 0
    for el in elements:
        tag = el.tag_name.lower()

        if tag in ['p', 'h1', 'h2', 'h3', 'h4']:
            text = el.text
            formatted_markdown += text + "\n\n"
            plain_text_parts.append(text)

        elif tag in ['ul', 'ol']:
            lis = el.find_elements(By.TAG_NAME, "li")
            list_text = ""
            for li in lis:
                list_text += "- " + li.text + "\n"
            formatted_markdown += list_text + "\n"
            plain_text_parts.append(list_text)

        elif tag == 'pre':
            try:
                lang_elem = el.find_elements(By.CSS_SELECTOR, "div.flex.items-center.text-sm")
                lang = lang_elem[0].text.lower() if lang_elem else "code"
                unique_lang_key = f"{lang}_{code_idx}"
                code_content = el.find_element(By.CSS_SELECTOR, "div.cm-content").text

                code_blocks[unique_lang_key] = code_content
                formatted_markdown += f"```{lang}\n{code_content}\n```\n\n"
                code_idx += 1
            except Exception as e:
                continue
        else:
            text = el.text
            formatted_markdown += text + "\n\n"
            plain_text_parts.append(text)

    return {
        "plain-text": "\n\n".join(plain_text_parts),
        "code-blocks": code_blocks,
        "formatted_markdown": formatted_markdown
    }
# Schema OpenHands/Standard API ki request capture karne ke liye
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    files: Optional[List[str]] = None
    temperature: Optional[float] = 1.0

    stream: Optional[bool] = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_driver()
    yield
    global driver
    print("\nCtrl+C detected! Shutting down gracefully...")
    if driver is not None:
        driver.quit()
        print("Chrome driver closed and resources freed safely. Bye!")

app = FastAPI(lifespan=lifespan)

@app.post("/v1/chat/completions")
async def openai_mock_api(req: ChatCompletionRequest):
    async with driver_lock:
        try:
            # ✨ THE HISTORY FIX: Hum ab purani baatein combine nahi karenge!
            # Sirf array ka sabse latest (aakhiri) message uthayenge.
            latest_msg = req.messages[-1]
            content = latest_msg.content if isinstance(latest_msg.content, str) else str(latest_msg.content)

            clean_prompt = content.strip()

            print(f"💅 Forwarding only the latest message to browser...")
            extracted_data = await send_and_extract(clean_prompt, files=req.files)

            return {

                "id": f"chatcmpl-{uuid.uuid4().hex}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": req.model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": extracted_data["formatted_markdown"]
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": len(clean_prompt) // 4,
                    "completion_tokens": len(extracted_data["formatted_markdown"]) // 4,
                    "total_tokens": (len(clean_prompt) + len(extracted_data["formatted_markdown"])) // 4
                }
            }
        except Exception as e:
            print(f"Server error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

class Query(BaseModel):
    prompt: str

@app.post("/ask")
async def ask_api(query: Query):
    async with driver_lock:
        try:
            return await send_and_extract(query.prompt)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# --- ✨ OLLAMA IMPERSONATION ROUTES ---

@app.get("/api/tags")
async def ollama_tags():
    """Tools jab local models ki list mangenge, toh hum apna fake model dikhayenge"""
    return {
        "models": [
            {
                "name": "chatgpt-scraper:latest", # Ye naam tumhare tool ke UI me dikhega
                "modified_at": datetime.now().isoformat(),
                "size": 7000000000, # Fake 7GB size taaki legit lage
                "details": {
                    "format": "gguf",
                    "family": "custom",
                    "parameter_size": "7B",
                    "quantization_level": "Q4_0"
                }
            }
        ]
    }

class OllamaMessage(BaseModel):
    role: str
    content: str

class OllamaChatRequest(BaseModel):
    model: str
    messages: List[OllamaMessage]
    stream: Optional[bool] = False

@app.post("/api/chat")
async def ollama_chat(req: OllamaChatRequest):
    """Ollama format me messages receive aur send karne ka route"""
    async with driver_lock:
        try:
            # Latest message uthao
            latest_msg = req.messages[-1]
            content = latest_msg.content if isinstance(latest_msg.content, str) else str(latest_msg.content)
            clean_prompt = content.strip()

            print(f"🕵️‍♀️ Ollama Disguise: Forwarding to browser...")
            extracted_data = await send_and_extract(clean_prompt)

            # Ollama ke specific JSON format me pack karke wapas bhejo
            return {
                "model": req.model,
                "created_at": datetime.now().isoformat(),
                "message": {
                    "role": "assistant",
                    "content": extracted_data["formatted_markdown"]
                },
                "done": True,
                "done_reason": "stop"
            }
        except Exception as e:
            print(f"Ollama endpoint error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("nchatgpt:app", host="0.0.0.0", port=8000, reload=False)
