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

# Global variables
driver = None
driver_lock = asyncio.Lock()

def init_driver():
    global driver
    if driver is None:
        print("🚀 Starting undetected chromedriver for Perplexity...")
        options = uc.ChromeOptions()
        # Ensure ye profile folder existing and logged in ho
        options.add_argument("--user-data-dir=/home/mohit/chrome-profile-perplexity")

        driver = uc.Chrome(options=options)
        driver.get("https://www.perplexity.ai/")
        print("✅ Profile loaded! Server is ready on current page.")
        time.sleep(5)

async def wait_for_stability(new_message_container):
    """Wait for text generation to stop by tracking text length and content"""
    print("⏳ Waiting for generation to stabilize...")
    last_text = ""
    stable_ticks = 0
    max_ticks = 240  # 240 * 0.5s = 120 seconds max wait
    
    for _ in range(max_ticks):
        try:
            current_text = new_message_container.text
            # Agar text 3 second (6 ticks) tak nahi badla, matlab generation DONE
            if current_text == last_text and len(current_text) > 0:
                stable_ticks += 1
                if stable_ticks >= 6: 
                    print("✅ Generation complete! (Text stabilized)")
                    return True
            else:
                stable_ticks = 0
                last_text = current_text
                if _ % 4 == 0 and len(current_text) > 0:
                    print(f"✍️ Perplexity is typing... (length: {len(current_text)})")
                    
        except Exception:
            pass # Ignore stale element errors during DOM updates
            
        await asyncio.sleep(0.5)
        
    print("❌ Wait timeout reached!")
    return False

async def send_and_extract(prompt_text: str):
    await asyncio.sleep(1)

    # 1. Gin lo page pe kitne 'markdown-content-' exist karte hain pehle se
    existing_messages = driver.find_elements(By.CSS_SELECTOR, "div[id^='markdown-content-']")
    initial_count = len(existing_messages)
    print(f"📊 Existing messages count before send: {initial_count}")

    # 2. Input box dhoondho (Robust approach for both homepage and thread)
    text_area = None
    selectors_to_try = ["#ask-input", "textarea", "[contenteditable='true']"]
    
    for selector in selectors_to_try:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                if el.is_displayed() and el.is_enabled():
                    text_area = el
                    break
            if text_area:
                break
        except Exception:
            continue

    if not text_area:
        raise Exception("Could not find the Perplexity input box!")

    # 3. Focus and Clear
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", text_area)
    await asyncio.sleep(0.5)
    driver.execute_script("arguments[0].focus();", text_area)
    
    # Send keys to clear (contenteditable safe)
    text_area.send_keys(Keys.CONTROL + "a")
    text_area.send_keys(Keys.BACKSPACE)
    await asyncio.sleep(0.3)

    # 4. Type Safely
    lines = prompt_text.split('\n')
    for i, line in enumerate(lines):
        text_area.send_keys(line)
        if i < len(lines) - 1:
            text_area.send_keys(Keys.SHIFT + Keys.ENTER)
            await asyncio.sleep(0.1)

    # 5. Send using ENTER
    await asyncio.sleep(0.5)
    text_area.send_keys(Keys.ENTER)
    print("📤 Message sent to Perplexity!")

    # 6. Wait for NEW message container to appear
    new_message_container = None
    wait_start = time.time()
    print("🕵️ Waiting for new response container to mount...")
    
    while time.time() - wait_start < 30: # 30 secs wait for response to start
        current_messages = driver.find_elements(By.CSS_SELECTOR, "div[id^='markdown-content-']")
        if len(current_messages) > initial_count:
            new_message_container = current_messages[-1]
            print(f"🎯 New container mounted! ID: {new_message_container.get_attribute('id')}")
            break
        await asyncio.sleep(1)

    if not new_message_container:
        raise Exception("Timeout! Perplexity did not start generating a response.")

    # 7. Wait for stabilization
    is_done = await wait_for_stability(new_message_container)
    if not is_done:
        raise Exception("Response generation didn't stabilize in time.")

    # 8. Extract Content (Simple Text Extraction for Perplexity)
    print("⛏️ Extracting content...")
    try:
        # Perplexity has nice formatted text inside these divs, including inline [1], [2] citations
        final_text = new_message_container.text
        print("✅ Extraction successful!")
    except Exception as e:
        print(f"⚠️ Extraction error: {e}")
        final_text = "Error extracting text."

    return {
        "plain-text": final_text,
        "formatted_markdown": final_text.strip()
    }


# --- API Models & Routes ---

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 1.0

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

            print("\n" + "="*40)
            print(f"📥 New Request to Perplexity")
            print("="*40)
            
            extracted_data = await send_and_extract(clean_prompt)

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

if __name__ == "__main__":
    # Running Perplexity on port 8003
    uvicorn.run("perplexity:app", host="0.0.0.0", port=8003, reload=False)