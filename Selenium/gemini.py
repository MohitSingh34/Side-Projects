import json
import time
import os
import asyncio
import emoji
import uvicorn
import uuid
import re
import pyperclip
from typing import List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# Global Variables
driver = None
gemini_window = None
action_lock = asyncio.Lock()

# ----------------- GEMINI AUTOMATION LOGIC -----------------

def init_gemini_driver():
    global driver, gemini_window
    if driver is None:
        print("🚀 Starting undetected chromedriver for Gemini...")
        options = uc.ChromeOptions()
        # Xubuntu chrome profile path
        options.add_argument("--user-data-dir=/home/mohit/chrome-profile-gemini")

        driver = uc.Chrome(
            options=options,
            driver_executable_path="/home/mohit/.cache/selenium/chromedriver/linux64/146.0.7680.153/chromedriver",
            version_main=146,
        )
        time.sleep(3)

        # Tab discovery
        driver.switch_to.new_window("tab")
        gemini_window = driver.current_window_handle
        driver.get("https://gemini.google.com/app")
        print("✅ Gemini Profile loaded! Thoda wait karte hain DOM set hone tak...")
        time.sleep(5)


async def wait_for_gemini_generation():
    """
    DOM monitor function. Stop button dikha = Generating. 
    Send button wapas aa gaya = Generation Complete.
    """
    await asyncio.sleep(2) # Initial buffer wait
    max_wait = 180 # 3 minutes max
    start_time = time.time()

    is_generating = True
    print("⏳ Waiting for Gemini to finish writing...")

    while time.time() - start_time < max_wait:
        async with action_lock:
            try:
                # Check agar "Send message" button wapas aa gaya hai
                send_btns = driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Send message']")
                
                # Check agar "Stop response" abhi bhi hai
                stop_btns = driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Stop response']")
                
                if not stop_btns and send_btns:
                    is_generating = False
                    break
            except Exception:
                pass
        
        await asyncio.sleep(1)

    if is_generating:
        print("⚠️ Warning: Timeout waiting for Gemini response.")
        return False
    
    print("✨ Generation complete!")
    return True


async def send_and_extract_gemini(prompt_text: str):
    global driver, gemini_window
    
    async with action_lock:
        driver.switch_to.window(gemini_window)
        await asyncio.sleep(1)

        # 1. Target the correct text box
        print("🔍 Locating text box...")
        text_area = driver.find_element(By.CSS_SELECTOR, "div.ql-editor[contenteditable='true']")
        
        driver.execute_script("arguments[0].scrollIntoView();", text_area)
        await asyncio.sleep(0.5)
        
        # Click and clear
        driver.execute_script("arguments[0].click();", text_area)
        text_area.send_keys(Keys.CONTROL + "a")
        text_area.send_keys(Keys.BACKSPACE)
        await asyncio.sleep(0.5)

        # Paste prompt
        pyperclip.copy(prompt_text)
        text_area.send_keys(Keys.CONTROL, "v")
        print("📋 Prompt pasted!")
        
        await asyncio.sleep(1)

        # 2. Hit the Send Button
        print("📤 Clicking Send...")
        send_btn = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Send message']")
        driver.execute_script("arguments[0].click();", send_btn)

    # Wait for generation to finish
    success = await wait_for_gemini_generation()
    if not success:
         return {"formatted_markdown": "SYSTEM ERROR: Timeout or failed to generate.", "error": True}

    # 3. Extract the Content
    async with action_lock:
        driver.switch_to.window(gemini_window)
        print("⛏️ Extracting response...")
        
        response_blocks = driver.find_elements(By.CSS_SELECTOR, "message-content")
        
        if not response_blocks:
            # Fallback
            response_blocks = driver.find_elements(By.CSS_SELECTOR, "div.markdown")

        latest_response = response_blocks[-1]
        
        formatted_markdown = ""
        plain_text_parts = []
        code_blocks = {}
        
        # DOM Extraction
        elements = latest_response.find_elements(By.XPATH, "./*")
        code_idx = 0
        
        for el in elements:
            tag = el.tag_name.lower()
            class_name = el.get_attribute("class") or ""
            
            if "code" in tag or "snippet" in class_name.lower():
                try:
                    code_content = el.text
                    unique_lang_key = f"code_{code_idx}"
                    code_blocks[unique_lang_key] = code_content
                    formatted_markdown += f"```\n{code_content}\n```\n\n"
                    code_idx += 1
                except Exception:
                    continue
            else:
                text = el.text
                if text.strip():
                    formatted_markdown += text + "\n\n"
                    plain_text_parts.append(text)

        md_text = formatted_markdown.strip()

    return {
        "plain-text": "\n\n".join(plain_text_parts),
        "code-blocks": code_blocks,
        "formatted_markdown": md_text,
    }

# ----------------- FASTAPI EXPOSURE -----------------

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    model_config = ConfigDict(extra="allow")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_gemini_driver()
    yield
    global driver
    print("\nShutting down gracefully...")
    if driver is not None:
        try:
            driver.quit()
        except Exception:
            pass

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/v1/chat/completions")
async def gemini_chat_api(req: ChatCompletionRequest):
    try:
        # Get the latest message
        latest_msg = req.messages[-1].content
        clean_prompt = emoji.demojize(latest_msg.strip())

        print("💅 Routing to Gemini tab...")
        
        extracted_data = await send_and_extract_gemini(clean_prompt)
        md_text = extracted_data.get("formatted_markdown", "")

        req_id = f"chatcmpl-{uuid.uuid4().hex}"
        created_time = int(time.time())

        return {
            "id": req_id,
            "object": "chat.completion",
            "created": created_time,
            "model": req.model,
            "choices": [
                {
                    "index": 0, 
                    "message": {
                        "role": "assistant",
                        "content": md_text
                    }, 
                    "finish_reason": "stop"
                }
            ],
        }

    except Exception as e:
        print(f"❌ ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("gemini:app", host="0.0.0.0", port=8001, reload=False)