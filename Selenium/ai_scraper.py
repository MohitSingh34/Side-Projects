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
from selenium.webdriver.common.keys import Keys
from datetime import datetime

# Core Paths
NOTES_DIR = "/home/mohit/Projects/notes"

# Global variables
driver = None
driver_lock = asyncio.Lock()
chatgpt_window = None
deepseek_window = None
perplexity_window = None

def init_driver():
    global driver, chatgpt_window, deepseek_window, perplexity_window
    if driver is None:
        print("🚀 Starting undetected chromedriver for ChatGPT, DeepSeek & Perplexity...")
        options = uc.ChromeOptions()
        options.add_argument("--user-data-dir=/home/mohit/chrome-profile-ucc")

        driver = uc.Chrome(options=options)
        
        # 1. Open ChatGPT
        driver.get("https://chatgpt.com/")
        chatgpt_window = driver.current_window_handle
        print("✅ ChatGPT Profile loaded!")
        
        # Wait 10 seconds before opening the next tab as requested
        time.sleep(10)
        
        # 2. Open DeepSeek
        driver.switch_to.new_window('tab')
        deepseek_window = driver.current_window_handle
        driver.get("https://chat.deepseek.com/")
        print("✅ DeepSeek Profile loaded!")
        
        # Wait 10 seconds before opening the next tab as requested
        time.sleep(10)
        
        # 3. Open Perplexity
        driver.switch_to.new_window('tab')
        perplexity_window = driver.current_window_handle
        driver.get("https://www.perplexity.ai/")
        print("✅ Perplexity Profile loaded! Server is ready.")
        
        # Switch back to ChatGPT just as a default
        driver.switch_to.window(chatgpt_window)
        time.sleep(3)

# ----------------- CHATGPT LOGIC -----------------
async def wait_for_chatgpt_response_to_complete():
    await asyncio.sleep(3)
    max_wait = 180 # Increased max wait
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

async def send_and_extract_chatgpt(prompt_text: str, files: Optional[List[str]] = None):
    # Ensuring we are on the ChatGPT tab
    driver.switch_to.window(chatgpt_window)
    await asyncio.sleep(1) # Extra stability delay before starting

    # --- File Upload Logic ---
    if files:
        try:
            file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
            for file_path in files:
                if os.path.exists(file_path):
                    file_input.send_keys(file_path)
                    print(f"Uploading file: {file_path}")
                    await asyncio.sleep(1.5) # Increased pause
                else:
                    print(f"File not found: {file_path}")
            
            print(f"Waiting for {len(files)} files to complete uploading...")
            max_wait = 60
            start = time.time()
            while time.time() - start < max_wait:
                remove_btns = driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Remove file']")
                if len(remove_btns) >= len(files):
                    print("All files seemingly uploaded!")
                    break
                await asyncio.sleep(1)
            await asyncio.sleep(2) # Extra buffer after upload
        except Exception as e:
            print(f"Error during file upload: {e}")

    try:
        text_area = driver.find_element(By.CSS_SELECTOR, "div#prompt-textarea")
        driver.execute_script("arguments[0].scrollIntoView();", text_area)
        await asyncio.sleep(1) # Extra delay
        driver.execute_script("arguments[0].click();", text_area)
        
        # Clear reliably
        text_area.send_keys(Keys.CONTROL + "a")
        text_area.send_keys(Keys.BACKSPACE)
        await asyncio.sleep(0.5)

        lines = prompt_text.split('\n')
        for i, line in enumerate(lines):
            text_area.send_keys(line)
            if i < len(lines) - 1:
                text_area.send_keys(Keys.SHIFT + Keys.ENTER)

        # Better delay before sending
        await asyncio.sleep(2.0)

        # Hit Enter
        text_area.send_keys(Keys.ENTER)
        
        # Wait a bit to let it register the enter
        await asyncio.sleep(2.0)

        is_done = await wait_for_chatgpt_response_to_complete()
        if not is_done:
            raise Exception("ChatGPT response generation timed out.")

        # Give UI a bit of time to fully settle before extracting
        await asyncio.sleep(2.0)
        
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

    except Exception as e:
        print(f"ChatGPT Extraction Error: {e}")
        raise e

# ----------------- DEEPSEEK LOGIC -----------------
async def send_and_extract_deepseek(prompt_text: str, files: Optional[List[str]] = None):
    driver.switch_to.window(deepseek_window)
    await asyncio.sleep(0.5)
    
    existing_messages = driver.find_elements(By.CSS_SELECTOR, "div.ds-markdown")
    initial_count = len(existing_messages)

    text_area = driver.find_element(By.CSS_SELECTOR, "textarea[placeholder='Message DeepSeek']")
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", text_area)
    driver.execute_script("arguments[0].focus();", text_area)

    text_area.send_keys(Keys.CONTROL + "a")
    text_area.send_keys(Keys.BACKSPACE)

    lines = prompt_text.split('\n')
    for i, line in enumerate(lines):
        text_area.send_keys(line)
        if i < len(lines) - 1:
            text_area.send_keys(Keys.SHIFT + Keys.ENTER)

    driver.execute_script("arguments[0].focus();", text_area)
    text_area.send_keys(Keys.ENTER)
    print("📤 Prompt sent to DeepSeek! Waiting for response...")

    new_message_container = None
    for _ in range(100):  
        current_messages = driver.find_elements(By.CSS_SELECTOR, "div.ds-markdown")
        if len(current_messages) > initial_count:
            new_message_container = current_messages[-1]
            break
        await asyncio.sleep(0.1)

    if not new_message_container:
        raise Exception("Timeout! DeepSeek ne naya response container start nahi kiya.")

    last_text = ""
    stable_ticks = 0
    max_ticks = 1200 

    print("✍️ Tracking text generation...")
    for _ in range(max_ticks):
        try:
            current_text = new_message_container.text
            if current_text == last_text and len(current_text) > 0:
                stable_ticks += 1
                if stable_ticks >= 5: 
                    print(f"✅ Generation complete! (Instant detect)")
                    break
            else:
                stable_ticks = 0
                last_text = current_text
        except Exception:
            pass 

        await asyncio.sleep(0.1)

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

# ----------------- PERPLEXITY LOGIC -----------------
async def wait_for_perplexity_stability(new_message_container):
    print("⏳ Waiting for Perplexity generation to stabilize...")
    last_text = ""
    stable_ticks = 0
    max_ticks = 240
    
    for _ in range(max_ticks):
        try:
            current_text = new_message_container.text
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
            pass 
            
        await asyncio.sleep(0.5)
        
    print("❌ Wait timeout reached!")
    return False

async def send_and_extract_perplexity(prompt_text: str, files: Optional[List[str]] = None):
    # Ensure we are on Perplexity tab
    driver.switch_to.window(perplexity_window)
    await asyncio.sleep(1)

    existing_messages = driver.find_elements(By.CSS_SELECTOR, "div[id^='markdown-content-']")
    initial_count = len(existing_messages)
    print(f"📊 Existing messages count before send: {initial_count}")

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

    driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", text_area)
    await asyncio.sleep(0.5)
    driver.execute_script("arguments[0].focus();", text_area)
    
    text_area.send_keys(Keys.CONTROL + "a")
    text_area.send_keys(Keys.BACKSPACE)
    await asyncio.sleep(0.3)

    lines = prompt_text.split('\n')
    for i, line in enumerate(lines):
        text_area.send_keys(line)
        if i < len(lines) - 1:
            text_area.send_keys(Keys.SHIFT + Keys.ENTER)
            await asyncio.sleep(0.1)

    await asyncio.sleep(0.5)
    text_area.send_keys(Keys.ENTER)
    print("📤 Prompt sent to Perplexity!")

    new_message_container = None
    wait_start = time.time()
    print("🕵️ Waiting for new response container to mount...")
    
    while time.time() - wait_start < 30:
        current_messages = driver.find_elements(By.CSS_SELECTOR, "div[id^='markdown-content-']")
        if len(current_messages) > initial_count:
            new_message_container = current_messages[-1]
            print(f"🎯 New container mounted! ID: {new_message_container.get_attribute('id')}")
            break
        await asyncio.sleep(1)

    if not new_message_container:
        raise Exception("Timeout! Perplexity did not start generating a response.")

    is_done = await wait_for_perplexity_stability(new_message_container)
    if not is_done:
        raise Exception("Response generation didn't stabilize in time.")

    print("⛏️ Extracting content...")
    try:
        final_text = new_message_container.text
        print("✅ Extraction successful!")
    except Exception as e:
        print(f"⚠️ Extraction error: {e}")
        final_text = "Error extracting text."

    # Return standard dictionary mimicking other bots
    return {
        "plain-text": final_text,
        "formatted_markdown": final_text.strip(),
        "code-blocks": {}
    }


# ----------------- FASTAPI ROUTES -----------------
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
            
            # ROUTING BASED ON MODEL NAME
            if req.model == 'deepseek-scraper':
                print(f"💅 Routing to DeepSeek tab...")
                extracted_data = await send_and_extract_deepseek(clean_prompt, files=req.files)
            elif req.model == 'perplexity-scraper':
                print(f"💅 Routing to Perplexity tab...")
                extracted_data = await send_and_extract_perplexity(clean_prompt, files=req.files)
            else:
                # Default to ChatGPT if 'gpt-scraper-mock' or anything else
                print(f"💅 Routing to ChatGPT tab...")
                extracted_data = await send_and_extract_chatgpt(clean_prompt, files=req.files)

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
            return await send_and_extract_chatgpt(query.prompt)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
# --- ✨ OLLAMA IMPERSONATION ROUTES (Kept for ChatGPT) ---
@app.get("/api/tags")
async def ollama_tags():
    return {
        "models": [
            {
                "name": "chatgpt-scraper:latest", 
                "modified_at": datetime.now().isoformat(),
                "size": 7000000000, 
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
    async with driver_lock:
        try:
            latest_msg = req.messages[-1]
            content = latest_msg.content if isinstance(latest_msg.content, str) else str(latest_msg.content)
            clean_prompt = content.strip()

            print(f"🕵️‍♀️ Ollama Disguise: Forwarding to ChatGPT browser...")
            extracted_data = await send_and_extract_chatgpt(clean_prompt)

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
    uvicorn.run("ai_scraper:app", host="0.0.0.0", port=8000, reload=False)
