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
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Core Paths
NOTES_DIR = "/home/mohit/Projects/notes"
PENDING_JSON_PATH = os.path.join(NOTES_DIR, "pending_deepseek.json")

# Global variables
driver = None
driver_lock = asyncio.Lock()

def init_driver():
    global driver
    if driver is None:
        print("🚀 Starting undetected chromedriver for DeepSeek...")
        options = uc.ChromeOptions()
        options.add_argument("--user-data-dir=/home/mohit/chrome-profile-ucc")

        driver = uc.Chrome(options=options)
        driver.get("https://chat.deepseek.com/")
        print("✅ Profile loaded! Server is ready on current page.")
        # Bas initial load pe wait karenge, baaki sab fast hoga
        time.sleep(5)

async def send_and_extract(prompt_text: str, files: Optional[List[str]] = None):
    # 1. Get initial count of messages BEFORE sending
    existing_messages = driver.find_elements(By.CSS_SELECTOR, "div.ds-markdown")
    initial_count = len(existing_messages)

    # 2. Textarea dhoondho aur instantly focus karo
    text_area = driver.find_element(By.CSS_SELECTOR, "textarea[placeholder='Message DeepSeek']")
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", text_area)
    driver.execute_script("arguments[0].focus();", text_area)

    # 3. Clear existing text
    text_area.send_keys(Keys.CONTROL + "a")
    text_area.send_keys(Keys.BACKSPACE)

    # 4. Type Safely (Multiline support)
    lines = prompt_text.split('\n')
    for i, line in enumerate(lines):
        text_area.send_keys(line)
        if i < len(lines) - 1:
            text_area.send_keys(Keys.SHIFT + Keys.ENTER)

    # 5. SEND (Instant hit)
    driver.execute_script("arguments[0].focus();", text_area)
    text_area.send_keys(Keys.ENTER)
    print("📤 Prompt sent! Waiting for response...")

    # 6. FAST POLLING: Wait for new message container to appear (max 10 sec wait)
    new_message_container = None
    for _ in range(100):  # 100 * 0.1s = 10 seconds timeout for DeepSeek to START thinking
        current_messages = driver.find_elements(By.CSS_SELECTOR, "div.ds-markdown")
        if len(current_messages) > initial_count:
            new_message_container = current_messages[-1]
            break
        await asyncio.sleep(0.1)

    if not new_message_container:
        raise Exception("Timeout! DeepSeek ne naya response container start nahi kiya.")

    # 7. FAST POLLING: Wait for generation to finish based on text stability
    last_text = ""
    stable_ticks = 0
    max_ticks = 1200 # 120 seconds max generation time

    print("✍️ Tracking text generation...")
    for _ in range(max_ticks):
        try:
            current_text = new_message_container.text
            if current_text == last_text and len(current_text) > 0:
                stable_ticks += 1
                if stable_ticks >= 5: # 5 ticks * 0.1s = 0.5 seconds of NO typing = DONE!
                    print(f"✅ Generation complete! (Instant detect)")
                    break
            else:
                stable_ticks = 0
                last_text = current_text
        except Exception:
            pass # Ignore stale element errors during fast re-renders

        await asyncio.sleep(0.1) # Super fast 100ms polling

    # 8. Extract Content (Smart Extraction + Fallback)
    print("⛏️ Extracting content...")
    formatted_markdown = ""
    plain_text_parts = []
    code_blocks = {}

    try:
        elements = new_message_container.find_elements(By.XPATH, "./*")
        code_idx = 0
        for el in elements:
            class_name = el.get_attribute("class") or ""

            if "md-code-block" in class_name:
                try:
                    lang_elems = el.find_elements(By.CSS_SELECTOR, "span.d813de27")
                    lang = lang_elems[0].text.lower() if lang_elems else "code"
                    pre_elem = el.find_element(By.CSS_SELECTOR, "pre")
                    code_content = pre_elem.text
                    unique_lang_key = f"{lang}_{code_idx}"
                    code_blocks[unique_lang_key] = code_content
                    formatted_markdown += f"```{lang}\n{code_content}\n```\n\n"
                    code_idx += 1
                except Exception:
                    continue
            else:
                text = el.text
                if text.strip():
                    formatted_markdown += text + "\n\n"
                    plain_text_parts.append(text)

    except Exception as e:
        print("⚠️ Falling back to raw text extraction.")
        raw_text = new_message_container.text
        formatted_markdown = raw_text
        plain_text_parts = [raw_text]

    return {
        "plain-text": "\n\n".join(plain_text_parts),
        "code-blocks": code_blocks,
        "formatted_markdown": formatted_markdown.strip()
    }

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
    print("\nShutting down gracefully...")
    if driver is not None:
        driver.quit()

app = FastAPI(lifespan=lifespan)

@app.post("/v1/chat/completions")
async def openai_mock_api(req: ChatCompletionRequest):
    async with driver_lock:
        try:
            latest_msg = req.messages[-1]
            content = latest_msg.content if isinstance(latest_msg.content, str) else str(latest_msg.content)
            clean_prompt = content.strip()

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
                }]
            }
        except Exception as e:
            print(f"❌ Server error: {e}")
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

if __name__ == "__main__":
    uvicorn.run("deepseek:app", host="0.0.0.0", port=8002, reload=False)
