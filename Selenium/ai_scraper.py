import json
import time
import os
import asyncio
import emoji
import uvicorn
import uuid
import re
import base64
import tempfile
import requests
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
import requests
import tempfile
import subprocess
import psutil


# Core Paths
NOTES_DIR = "/home/mohit/Projects/notes"

# 👇 YAHAN SE ORCHESTRATOR CHOOSE KAR 👇
# Options: "chatgpt" ya "deepseek"
ORCHESTRATOR_MODEL = "deepseek"
# 👆 YAHAN TAK 👆

# Global variables
driver = None
action_lock = asyncio.Lock()
chatgpt_window = None
deepseek_window = None
gemini_window = None  # 🚀 ADD THIS
orchestrator_window = None
agents_registry = {}  # 🚀 NEW: Dynamic Tab Registry (Stores ALL open tabs)

# ----------------- DYNAMIC AGENT SCANNER -----------------
# ----------------- DYNAMIC AGENT SCANNER -----------------
def update_agents_registry():
    global driver, chatgpt_window, deepseek_window, gemini_window, orchestrator_window, agents_registry
    print("🔍 Scanning all open tabs to register Agents...")
    agents_registry.clear()
    cgpt_count = 1
    ds_count = 1
    gm_count = 1

    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        url = driver.current_url

        if "chatgpt.com" in url:
            if chatgpt_window is None:
                chatgpt_window = handle
            
            # Agar ye tab orchestrator ka hai, toh clearly mark karo
            if (ORCHESTRATOR_MODEL.lower() == "chatgpt" and orchestrator_window is None) or handle == orchestrator_window:
                orchestrator_window = handle
                agent_id = "orchestrator-chatgpt (Not Agent)"
                print(f"👑 ORCHESTRATOR ASSIGNED: {agent_id}")
            else:
                agent_id = f"agent-chatgpt-{cgpt_count}"
                cgpt_count += 1
                print(f"✅ Registered worker: {agent_id}")
            
            agents_registry[agent_id] = handle

        elif "chat.deepseek.com" in url:
            if deepseek_window is None:
                deepseek_window = handle
            
            # Agar ye tab orchestrator ka hai, toh clearly mark karo
            if (ORCHESTRATOR_MODEL.lower() == "deepseek" and orchestrator_window is None) or handle == orchestrator_window:
                orchestrator_window = handle
                agent_id = "orchestrator-deepseek (Not Agent)"
                print(f"👑 ORCHESTRATOR ASSIGNED: {agent_id}")
            else:
                agent_id = f"agent-deepseek-{ds_count}"
                ds_count += 1
                print(f"✅ Registered worker: {agent_id}")
            
            agents_registry[agent_id] = handle

        elif "gemini.google.com" in url:
            if gemini_window is None:
                gemini_window = handle
            
            # Agar ye tab orchestrator ka hai, toh clearly mark karo
            if (ORCHESTRATOR_MODEL.lower() == "gemini" and orchestrator_window is None) or handle == orchestrator_window:
                orchestrator_window = handle
                agent_id = "orchestrator-gemini (Not Agent)"
                print(f"👑 ORCHESTRATOR ASSIGNED: {agent_id}")
            else:
                agent_id = f"agent-gemini-{gm_count}"
                gm_count += 1
                print(f"✅ Registered worker: {agent_id}")
            
            agents_registry[agent_id] = handle
# ---------------------------------------------------------

# ----------------- CHATGPT LOGIC -----------------
def init_driver():
    global driver, chatgpt_window, deepseek_window, gemini_window, orchestrator_window, agents_registry
    if driver is None:
        print("🚀 Starting undetected chromedriver for ChatGPT & DeepSeek...")
        options = uc.ChromeOptions()
        options.add_argument("--user-data-dir=/home/mohit/chrome-profile-v4")

        driver = uc.Chrome(
            options=options,
            driver_executable_path="/home/mohit/.cache/selenium/chromedriver/linux64/146.0.7680.153/chromedriver",
            version_main=146,
        )

        # Give browser time to restore previous session tabs
        time.sleep(5)

        # 1. Discover already open tabs dynamically
        print("🔍 Scanning all open tabs to register Agents...")

        # 1. Discover already open tabs dynamically
        update_agents_registry()

        # 2. Open any missing tabs
        # 2. 🚀 FIXED: Only open the orchestrator tab, DO NOT auto-spawn agents
        # Agents will ONLY be launched via /v1/launch_agent API
        if orchestrator_window is None:
            driver.switch_to.new_window("tab")
            orchestrator_window = driver.current_window_handle
            if ORCHESTRATOR_MODEL.lower() == "deepseek":
                driver.get("https://chat.deepseek.com/")
                print("✅ Orchestrator (DeepSeek) loaded!")
            elif ORCHESTRATOR_MODEL.lower() == "gemini":
                driver.get("https://gemini.google.com/app")
                print("✅ Orchestrator (Gemini) loaded!")
            else:
                driver.get("https://chatgpt.com/")
                print("✅ Orchestrator (ChatGPT) loaded!")
            time.sleep(3)

        # 🚀 FIX: Scan and register agents AFTER opening the new tabs!
        update_agents_registry()
        time.sleep(3)

def copy_text_to_clipboard(text: str):
    subprocess.run(['xclip', '-selection', 'clipboard'], input=text.encode('utf-8'), check=True)
# ----------------- GEMINI LOGIC 🚀 -----------------
async def wait_for_gemini_generation(window):
    await asyncio.sleep(2) 
    max_wait = 180 
    start_time = time.time()
    is_generating = True
    print("⏳ Waiting for Gemini to finish writing...")

    while time.time() - start_time < max_wait:
        async with action_lock: # Lock only for checking
            try:
                driver.switch_to.window(window)
                send_btns = driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Send message']")
                stop_btns = driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Stop response']")
                if not stop_btns and send_btns:
                    is_generating = False
                    break
            except Exception:
                pass
        
        if not is_generating:
            break
        await asyncio.sleep(1)

    if is_generating:
        print("⚠️ Warning: Timeout waiting for Gemini response.")
        return False
    return True

def get_text_from_clipboard():
    # Tumhare Linux/Xubuntu system pe xclip use karke clipboard read karna
    result = subprocess.run(['xclip', '-selection', 'clipboard', '-o'], capture_output=True, text=True)
    return result.stdout

import subprocess
import asyncio
import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from typing import Optional, List
import requests

async def send_and_extract_gemini(prompt_text: str, files: Optional[List[str]] = None, target_window=None):
    window = target_window if target_window else gemini_window
    
    async with action_lock:
        driver.switch_to.window(window)
        await asyncio.sleep(1)

        print("🔍 Locating Gemini text box...")
        
        # 🚀 FIX 1: Network Drop / Disconnect Recovery
        try:
            text_area = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.ql-editor[contenteditable='true']"))
            )
        except Exception:
            print("⚠️ Gemini text box not found! Page might have crashed or disconnected. Refreshing...")
            driver.refresh()
            await asyncio.sleep(6) # Wait for page to reload fully
            text_area = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.ql-editor[contenteditable='true']"))
            )

        driver.execute_script("arguments[0].scrollIntoView();", text_area)
        await asyncio.sleep(0.5)
        
        # 0. Ensure focus & Clear Box
        driver.execute_script("arguments[0].click();", text_area)
        text_area.send_keys(Keys.CONTROL + "a")
        text_area.send_keys(Keys.BACKSPACE)
        await asyncio.sleep(0.5)

        # 🚀 1. PASTE FILES FIRST
        print(f"Checking for existence of files in clipboard...")
        if files:
            for file_path in files:
                if os.path.exists(file_path):
                    print(f"📎 Loading file to clipboard: {file_path}")
                    requests.post("http://localhost:8761/v1/system/clipboard/file", json={"filepath": file_path})
                    
                    await asyncio.sleep(1)
                    text_area.send_keys(Keys.CONTROL, "v")
                    print("⏳ Waiting for image to render in Gemini UI...")
                    await asyncio.sleep(2.5)

        # 🚀 2. COPY & PASTE PROMPT TEXT
        if prompt_text:
            print("📋 Copying prompt text to clipboard...")
            copy_text_to_clipboard(prompt_text)
            await asyncio.sleep(0.5)
            
            driver.execute_script("arguments[0].click();", text_area)
            text_area.send_keys(Keys.CONTROL, "v")
            print("📋 Prompt pasted in Gemini!")
            await asyncio.sleep(1)
            
        # 🚀 3. CLICK SEND
        print("📤 Locating Send Button...")
        send_btn = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Send message']")
        
        start_wait = time.time()
        while send_btn.get_attribute("disabled") and time.time() - start_wait < 10:
            await asyncio.sleep(0.5)
            
        driver.execute_script("arguments[0].click();", send_btn)

    # Lock released for waiting
    success = await wait_for_gemini_generation(window)
    await asyncio.sleep(2) # 🚀 FIX 2: Give DOM extra 2 seconds to finalize rendering!

    if not success:
         return {"formatted_markdown": "SYSTEM ERROR: Timeout or failed to generate.", "error": True}

    # --- 🚀 NEW COPY BUTTON EXTRACTION LOGIC 🚀 ---
    async with action_lock:
        driver.switch_to.window(window)
        print("⛏️ Clicking Copy Button to extract raw response from Gemini...")

        md_text = ""
        try:
            # Saare copy buttons dhundho
            copy_buttons = driver.find_elements(By.CSS_SELECTOR, "button[data-test-id='copy-button']")

            if copy_buttons:
                # Hamesha latest (sabse neeche wale) message ka copy button click karna hai
                latest_copy_btn = copy_buttons[-1]

                # Viewport mein scroll karo taaki click fail na ho
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", latest_copy_btn)
                await asyncio.sleep(0.5)

                # JavaScript se click karo
                driver.execute_script("arguments[0].click();", latest_copy_btn)
                print("📋 Copy button clicked successfully!")

                # Clipboard mein data aane ka thoda sa wait karo
                await asyncio.sleep(1.5)

                # Linux system ke clipboard se data nikalne ke liye xclip ka use
                result = subprocess.run(['xclip', '-selection', 'clipboard', '-o'], capture_output=True, text=True)
                md_text = result.stdout.strip()
                
                # 🚀 FIX 3: CLEAN UP GEMINI'S MARKDOWN ESCAPING 🚀
                # Gemini adds backslashes before special characters in markdown copy. Let's remove them!
                # 🚀 FIX 3: CLEAN UP GEMINI'S MARKDOWN ESCAPING 🚀
                # Gemini adds backslashes before special characters in markdown copy. Let's remove them!
                md_text = md_text.replace("\\<", "<")
                md_text = md_text.replace("\\>", ">")
                md_text = md_text.replace("\\_", "_")
                md_text = md_text.replace("\\[", "[")
                md_text = md_text.replace("\\]", "]")
                md_text = md_text.replace("\\*", "*")
                md_text = md_text.replace("\\`", "`")  # Code blocks/inline code
                md_text = md_text.replace("\\#", "#")  # Headers
                md_text = md_text.replace("\\+", "+")  # Lists
                md_text = md_text.replace("\\-", "-")  # Lists
                md_text = md_text.replace("\\.", ".")  # Numbered lists
                md_text = md_text.replace("\\!", "!")  # Images
                md_text = md_text.replace("\\(", "(")  # Links
                md_text = md_text.replace("\\)", ")")  # Links
                md_text = md_text.replace("\\{", "{")
                md_text = md_text.replace("\\}", "}")
                md_text = md_text.replace("\\|", "|")  # Tables
                
            else:
                print("⚠️ Warning: Copy button not found. Using fallback text extraction.")
                # Fallback in case UI changes
                response_blocks = driver.find_elements(By.CSS_SELECTOR, "message-content")
                if response_blocks:
                    md_text = driver.execute_script("return arguments[0].innerText;", response_blocks[-1])
                else:
                    md_text = "Error: Could not extract text."

        except Exception as e:
            print(f"⚠️ Error during extraction: {e}")
            md_text = f"Error extracting text: {e}"

        # Debugging ke liye save karna
        try:
            with open("intercepted_cline_response.txt", "w", encoding="utf-8") as f:
                f.write(md_text)
            print("📝 Surprise! Response successfully intercepted and saved to 'intercepted_cline_response.txt'")
        except Exception as e:
            pass

    return {
        "plain-text": md_text,
        "code-blocks": {}, # Empty chhod sakte hain, sab markdown me aa gaya hai
        "formatted_markdown": md_text,
    }
# 🚀 SMART WAIT WITH ACTION LOCK
async def wait_for_chatgpt_response_to_complete(window):
    await asyncio.sleep(3)
    max_wait = 300  # 5 minutes max wait
    start_time = time.time()

    while time.time() - start_time < max_wait:
        is_ready = False
        async with action_lock:  # 🚀 Lock only for browser check
            try:
                driver.switch_to.window(window)
                # Prevent detachments by actively scrolling it to the bottom
                messages = driver.find_elements(
                    By.CSS_SELECTOR, "div[data-message-author-role='assistant']"
                )
                if messages:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'end'});",
                        messages[-1],
                    )

                # Check for voice button (means it's idle and ready)
                voice_btn = driver.find_elements(
                    By.CSS_SELECTOR, "button[aria-label='Start Voice']"
                )
                if voice_btn:
                    is_ready = True

                # Check for send button being re-enabled
                send_btn = driver.find_elements(
                    By.CSS_SELECTOR, "button[data-testid='send-button']"
                )
                if send_btn and not send_btn[0].get_attribute("disabled"):
                    is_ready = True
            except Exception:
                pass
        
        if is_ready:
            await asyncio.sleep(2)
            return True
        
        # 🚀 Lock released! Other agents can check their tabs
        await asyncio.sleep(3)
    return False

async def send_and_extract_chatgpt(
    prompt_text: str, files: Optional[List[str]] = None, target_window=None
):
    # Ensuring we are on the ChatGPT tab
    window = target_window if target_window else chatgpt_window

    # 🚀 CRITICAL: Type message in browser
    async with action_lock:
        driver.switch_to.window(window)
        await asyncio.sleep(1)  # Extra stability delay before starting

        text_area = driver.find_element(By.CSS_SELECTOR, "div#prompt-textarea")
        driver.execute_script("arguments[0].scrollIntoView();", text_area)
        await asyncio.sleep(1)
        driver.execute_script("arguments[0].click();", text_area)

        # Clear reliably pehle hi kar lo taaki uploaded file baad me erase na ho
        text_area.send_keys(Keys.CONTROL + "a")
        text_area.send_keys(Keys.BACKSPACE)
        await asyncio.sleep(0.5)

        # 🚀 1. PASTE FILES FIRST
        if files:
            for file_path in files:
                if os.path.exists(file_path):
                    print(f"📎 Loading file to clipboard: {file_path}")
                    requests.post("http://localhost:8761/v1/system/clipboard/file", json={"filepath": file_path})
                    
                    await asyncio.sleep(0.5) # X11 Clipboard ko sync hone ka time
                    text_area.send_keys(Keys.CONTROL, "v")
                    print("⏳ Waiting for image upload in ChatGPT...")
                    await asyncio.sleep(2.5) # Local file fast hoti hai, 2.5s is enough

        # 🚀 2. COPY & PASTE PROMPT TEXT
        if prompt_text:
            print("📋 Copying prompt text to clipboard...")
            copy_text_to_clipboard(prompt_text)
            await asyncio.sleep(0.5)
            
            # Re-focus and paste text
            driver.execute_script("arguments[0].click();", text_area)
            text_area.send_keys(Keys.CONTROL, "v")

        prompt_len = len(prompt_text)
        wait_time = 2.0 
        print(f"⏳ Waiting {wait_time}s for DOM to process prompt...")
        await asyncio.sleep(wait_time)

        # 🚀 3. SMART CLICK SEND (Waits for upload to finish)
        print("📤 Locating Send Button in ChatGPT...")
        start_wait = time.time()
        send_btn_clicked = False
        
        # Max 30 seconds wait karenge file upload hone ka
        while time.time() - start_wait < 30:
            try:
                send_btns = driver.find_elements(By.CSS_SELECTOR, "button[data-testid='send-button']")
                if send_btns:
                    send_btn = send_btns[0]
                    # Check if button is visible and NOT disabled (meaning upload is done)
                    if not send_btn.get_attribute("disabled"):
                        driver.execute_script("arguments[0].click();", send_btn)
                        send_btn_clicked = True
                        break
            except Exception:
                pass
            await asyncio.sleep(0.5)
            
        if not send_btn_clicked:
            print("⚠️ Warning: Send button didn't enable (maybe network issue). Forcing ENTER fallback...")
            text_area.send_keys(Keys.ENTER)

        print("📤 Prompt & File(s) sent to ChatGPT! Waiting for response...")

    # 🚀 LOCK RELEASED! Let other agents type their prompts while this one waits
    await asyncio.sleep(2.0)

    is_done = await wait_for_chatgpt_response_to_complete(window)
    if not is_done:
        print("⚠️ SYSTEM ERROR: ChatGPT response generation timed out or failed.")
        return {"formatted_markdown": "SYSTEM ERROR: Failed to generate response. The input might be too long, or the tab timed out.", "error": True}

    # 🚀 CRITICAL: Extract response from browser
    async with action_lock:
        driver.switch_to.window(window)

        messages = driver.find_elements(
            By.CSS_SELECTOR, "div[data-message-author-role='assistant']"
        )
        latest_message = messages[-1]

        formatted_markdown = ""
        plain_text_parts = []
        code_blocks = {}

        elements = latest_message.find_elements(
            By.CSS_SELECTOR, "div.markdown.prose > *"
        )

        code_idx = 0
        for el in elements:
            tag = el.tag_name.lower()

            if tag in ["p", "h1", "h2", "h3", "h4"]:
                text = el.text
                formatted_markdown += text + "\n\n"
                plain_text_parts.append(text)

            elif tag in ["ul", "ol"]:
                lis = el.find_elements(By.TAG_NAME, "li")
                list_text = ""
                for li in lis:
                    list_text += "- " + li.text + "\n"
                formatted_markdown += list_text + "\n"
                plain_text_parts.append(list_text)

            elif tag == "pre":
                try:
                    lang_elem = el.find_elements(
                        By.CSS_SELECTOR, "div.flex.items-center.text-sm"
                    )
                    lang = lang_elem[0].text.lower() if lang_elem else "code"
                    unique_lang_key = f"{lang}_{code_idx}"
                    code_content = el.find_element(
                        By.CSS_SELECTOR, "div.cm-content"
                    ).text

                    code_blocks[unique_lang_key] = code_content
                    formatted_markdown += f"```{lang}\n{code_content}\n```\n\n"
                    code_idx += 1
                except Exception as e:
                    continue
            else:
                text = el.text
                formatted_markdown += text + "\n\n"
                plain_text_parts.append(text)

        md_text = formatted_markdown.strip()
        try:
            with open("intercepted_cline_response.txt", "w", encoding="utf-8") as f:
                f.write(md_text)
            print(
                "📝 Suprise! Response successfully intercepted and saved to 'intercepted_cline_response.txt'"
            )
        except Exception as e:
            print(f"⚠️ Error saving intercepted response: {e}")

    return {
        "plain-text": "\n\n".join(plain_text_parts),
        "code-blocks": code_blocks,
        "formatted_markdown": md_text,
    }
        
    # ----------------- DEEPSEEK LOGIC -----------------
async def send_and_extract_deepseek(
    prompt_text: str, files: Optional[List[str]] = None, target_window=None
):
    # Select the correct window based on whether it's acting as orchestrator
    window = target_window if target_window else deepseek_window

    # Capture LAST wrapper's HTML before sending (user suggested class `_4f9bf79` for the outer block)
    previous_last_html = ""
    async with action_lock:  # 🚀 Lock to capture initial state
        driver.switch_to.window(window)
        try:
            old_msgs = driver.find_elements(By.CSS_SELECTOR, "div._4f9bf79")
            if old_msgs:
                previous_last_html = driver.execute_script(
                    "return arguments[0].innerHTML;", old_msgs[-1]
                )
        except Exception:
            pass

        # Type and send the prompt
        text_area = driver.find_element(
            By.CSS_SELECTOR, "textarea[placeholder='Message DeepSeek']"
        )
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});",
            text_area,
        )
        driver.execute_script("arguments[0].focus();", text_area)

        text_area.send_keys(Keys.CONTROL + "a")
        text_area.send_keys(Keys.BACKSPACE)
        await asyncio.sleep(0.5)

        

        copy_text_to_clipboard(prompt_text)
        text_area.send_keys(Keys.CONTROL, "v")

        prompt_len = len(prompt_text)
        if prompt_len <= 100:
            wait_time = 3.0
        elif prompt_len <= 700:
            wait_time = 4.0
        else:
            wait_time = 4.0

        print(
            f"📋 Pasted prompt in DeepSeek (len: {prompt_len}), waiting {wait_time}s for DOM..."
        )
        await asyncio.sleep(wait_time)

        driver.execute_script("arguments[0].focus();", text_area)
        text_area.send_keys(Keys.ENTER)
        print("📤 Prompt sent to DeepSeek! Waiting for response...")

    # 🚀 LOCK RELEASED! Let other agents type their prompts

    # Wait for a NEW message to appear (detecting change in the last `_4f9bf79` wrapper)
    new_message_found = False
    for _ in range(150):  # 150 * 0.4s = 60 seconds
        async with action_lock:  # 🚀 Brief lock only to check
            try:
                driver.switch_to.window(window)
                current_msgs = driver.find_elements(By.CSS_SELECTOR, "div._4f9bf79")
                if current_msgs:
                    current_html = driver.execute_script(
                        "return arguments[0].innerHTML;", current_msgs[-1]
                    )
                    if current_html != previous_last_html and current_html.strip() != "":
                        new_message_found = True
            except Exception:
                pass
        
        if new_message_found:
            break
        await asyncio.sleep(0.4)

    if not new_message_found:
        print("⚠️ SYSTEM ERROR: DeepSeek did not start generating.")
        return {"formatted_markdown": "SYSTEM ERROR: DeepSeek did not respond. The input might be too long or the browser is stuck. Please shorten your prompt.", "error": True}

    # --- NEW TRACKING LOGIC (3-second compare checking HTML NOT just text) ---
    # --- NEW TRACKING LOGIC (Smart Stabilization for DeepSeek Pauses) ---
    last_html = ""
    stable_count = 0  # 🚀 Naya variable jo consecutive pauses ginega
    max_ticks_new = 100  # 100 * 3s = 300 secs (5 mins) timeout
    print("✍️ Tracking generation dynamically (HTML + Refs) interval scanning...")

    for _ in range(max_ticks_new):
        async with action_lock:  # 🚀 Lock only to check HTML
            try:
                # IMPORTANT: Re-fetch every loop to bypass StaleElementReference
                driver.switch_to.window(window)
                current_msgs = driver.find_elements(By.CSS_SELECTOR, "div._4f9bf79")
                if not current_msgs:
                    await asyncio.sleep(3)
                    continue

                latest_container = current_msgs[-1]

                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'end'});",
                    latest_container,
                )

                # Using innerHTML tracks EVERYTHING (all tags, new blocks)
                current_html = driver.execute_script(
                    "return arguments[0].innerHTML;", latest_container
                )

                if not current_html:
                    current_html = ""

                if current_html == last_html and len(current_html) > 0:
                    stable_count += 1
                    # 🚀 Yahan hum check kar rahe hain: Agar lagatar 3 baar (3x3 = 9 seconds) HTML change nahi hua, tabhi Final maano!
                    if stable_count >= 3:
                        print(f"✅ Generation complete! (HTML structure stabilized perfectly)")
                        break
                else:
                    last_html = current_html
                    stable_count = 0  # 🚀 Agar DeepSeek ne wapas type karna shuru kiya, toh counter reset kar do!

            except Exception as e:
                pass

        await asyncio.sleep(3)

    # 🚀 CRITICAL: Extract response from browser
    async with action_lock:
        driver.switch_to.window(window)
        
        print("⛏️ Extracting content...")
        formatted_markdown = ""
        plain_text_parts = []
        code_blocks = {}

        # Extract final content re-fetching to prevent crashes
        try:
            final_msgs = driver.find_elements(By.CSS_SELECTOR, "div._4f9bf79")
            final_container = final_msgs[-1]

            # Original element iteration inside the wrapper
            markdown_divs = final_container.find_elements(
                By.CSS_SELECTOR, "div.ds-markdown"
            )
            if markdown_divs:
                extraction_target = markdown_divs[0]
                elements = extraction_target.find_elements(By.XPATH, "./*")
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
            else:
                final_text = driver.execute_script(
                    "return arguments[0].innerText || arguments[0].textContent;",
                    final_container,
                )
                formatted_markdown = final_text.strip()
                plain_text_parts = [formatted_markdown]

        except Exception as e:
            print(f"⚠️ Extraction error: {e}")
            formatted_markdown = "Error extracting text."
            plain_text_parts = [formatted_markdown]

        md_text = formatted_markdown.strip()

        # 👇 YAHAN SE EDIT START HAI 👇
        try:
            with open("intercepted_cline_response.txt", "w", encoding="utf-8") as f:
                f.write(md_text)
            print(
                "📝 Suprise! Response successfully intercepted and saved to 'intercepted_cline_response.txt'"
            )
        except Exception as e:
            print(f"⚠️ Error saving intercepted response: {e}")
        # 👆 YAHAN TAK 👆

    return {
        "plain-text": "\n\n".join(plain_text_parts),
        "code-blocks": code_blocks,
        "formatted_markdown": md_text,
    }

# ----------------- JINA READER AGENT -----------------
# ----------------- JINA READER AGENT -----------------
async def fetch_from_jina(prompt_text: str, **kwargs):
    import re
    # Extract URL from prompt
    url_match = re.search(r'(https?://[^\s]+)', prompt_text)
    if not url_match:
        return {"formatted_markdown": "SYSTEM ERROR: No valid URL found in the prompt for Jina Agent to read.", "error": True}
    
    url = url_match.group(1)
    print(f"🌐 Jina Agent fetching FRESH URL: {url}")
    try:
        def get_jina():
            # 🚀 NAYA FIX: Headers add kiye cache bypass karne ke liye
            headers = {
                "X-No-Cache": "true"
            }
            return requests.get(f"https://r.jina.ai/{url}", headers=headers, timeout=45).text
            
        content = await asyncio.to_thread(get_jina)
        return {"formatted_markdown": content, "error": False}
    except Exception as e:
        return {"formatted_markdown": f"SYSTEM ERROR: Jina API crashed. Details: {str(e)}", "error": True}
# -----------------------------------------------------
# -----------------------------------------------------

# ----------------- FASTAPI ROUTES -----------------
from typing import Any
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse


class ChatMessage(BaseModel):
    role: str
    content: Any  # Allowing list of dicts for vision/tool results


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    tools: Optional[List[dict]] = None
    files: Optional[List[str]] = None
    temperature: Optional[float] = 1.0
    stream: Optional[bool] = False
    model_config = ConfigDict(extra="allow")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_driver()
    yield
    global driver
    print("\nShutting down gracefully...")
    if driver is not None:
        try:
            # 1. Grab PID before quitting
            pid = driver.browser_pid
            driver.quit()
            
            # 2. Force kill the main driver process if it's stubborn
            if pid:
                try:
                    os.kill(pid, 9)
                except Exception:
                    pass
            
            # 🚀 3. ZOMBIE PROCESS CLEANUP: Kill any stray Chrome instances using our profile
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = str(proc.cmdline())
                    if 'chrome' in proc.name().lower() and 'chrome-profile-v4' in cmdline:
                        proc.kill()
                        print(f"🔫 Killed zombie Chrome process (PID: {proc.pid})")
                except Exception:
                    pass
        except Exception as e:
            print(f"Cleanup error: {e}")

app = FastAPI(lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: FastAPI.requests.Request, exc: RequestValidationError
):
    print("\n❌ FASTAPI 422 UNPROCESSABLE CONTENT ERROR ❌")
    print("Received Body:", await request.body())
    print("Validation Error Details:")
    for error in exc.errors():
        print(error)
    print("-------------------------------------------\n")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )


# CORS enabled so browser fetch API (index.html / groupChat.html) won't get blocked!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- 🤖 MODELS ENDPOINT (Dynamic Agents List) 🤖 ---
@app.get("/v1/models")
async def list_models():
    current_time = int(time.time())

    # Default models for general use
    models_list = [
        {"id": "agent-jina", "object": "model", "created": current_time, "owned_by": "custom-scraper"} # 🚀 Added Jina
    ]

    # 🚀 Dynamically add ALL registered tabs as models
    for agent_id in agents_registry.keys():
        models_list.append(
            {
                "id": agent_id,
                "object": "model",
                "created": current_time,
                "owned_by": "custom-scraper",
            }
        )

    return {
        "object": "list",
        "data": models_list,
    }
# ---------------------------------------------------------

@app.post("/v1/chat/completions")
async def openai_mock_api(req: ChatCompletionRequest):
    try:
        # ✨ PROPER CONTENT EXTRACTION (Handling Lists & System Prompts)
        # 📸 --- EXTRACT SCREENSHOTS FROM CLINE ---
        if req.files is None:
            req.files = []

        temp_files_to_cleanup = []
        for msg in req.messages:
            if isinstance(msg.content, list):
                for item in msg.content:
                    if isinstance(item, dict) and item.get("type") == "image_url":
                        img_url = item.get("image_url", {}).get("url", "")
                        if img_url.startswith("data:image"):
                            try:
                                # Base64 string se image decode karke temp file me save karna
                                header, encoded = img_url.split(",", 1)
                                img_data = base64.b64decode(encoded)
                                tmp_file = tempfile.NamedTemporaryFile(
                                    delete=False, suffix=".png"
                                )
                                tmp_file.write(img_data)
                                tmp_file.close()

                                # Is file path ko ChatGPT ke upload logic ko feed kar do
                                req.files.append(tmp_file.name)
                                temp_files_to_cleanup.append(tmp_file.name)
                                print(
                                    f"📸 Cline sent an image! Saved locally to {tmp_file.name} for upload."
                                )
                            except Exception as e:
                                print(
                                    f"⚠️ Failed to process base64 image from Cline: {e}"
                                )
        # 📸 --------------------------------------
        is_first_turn = len(req.messages) <= 3

        def extract_text(msg):
            if isinstance(msg.content, list):
                return "\n".join(
                    [
                        item.get("text", "")
                        for item in msg.content
                        if isinstance(item, dict) and item.get("type") == "text"
                    ]
                )
            elif isinstance(msg.content, str):
                return msg.content
            return str(msg.content)

        if is_first_turn:
            # First query: Provide full context (System prompt + User prompt)
            content = "\n\n--- NEXT MESSAGE ---\n\n".join(
                [extract_text(m) for m in req.messages]
            )
        else:
            # Subsequent queries: Only send the latest message to avoid looping history
            content = extract_text(req.messages[-1])


        clean_prompt = content.strip()
        # ✨ EMOJI FIX: ChromeDriver fails on non-BMP characters (like emojis). Convert to ascii text!
        # deemoji_prompt = emoji.demojize(clean_prompt)
        prompt_to_send = clean_prompt  # Use clean_prompt directly, no de-emojizing

        # Check if tools are provided (orchestrator mode)
        is_orchestrator = False
        if hasattr(req, "tools") and req.tools:
            is_orchestrator = True

        # 🚀 MULTI-AGENT DYNAMIC ROUTING 🚀
        model_req = req.model.lower()
        active_func = None
        active_window = None

        # 🚀 ROUTING LOGIC
        model_req = req.model.lower()
        active_func, active_window = None, None

        if model_req == "agent-jina":
            active_func, active_window = fetch_from_jina, "jina_virtual"
        elif model_req in agents_registry:
            active_window = agents_registry[model_req]
            if "chatgpt" in model_req: active_func = send_and_extract_chatgpt
            elif "gemini" in model_req: active_func = send_and_extract_gemini # 🚀 Route Gemini
            else: active_func = send_and_extract_deepseek
        elif is_orchestrator or True: # Default fallback
            active_window = orchestrator_window
            if ORCHESTRATOR_MODEL.lower() == "deepseek": active_func = send_and_extract_deepseek
            elif ORCHESTRATOR_MODEL.lower() == "gemini": active_func = send_and_extract_gemini # 🚀 Route Gemini Orch
            else: active_func = send_and_extract_chatgpt

        else:
            print(
                f"💅 Routing to Default Orchestrator ({ORCHESTRATOR_MODEL.upper()}) tab..."
            )
            active_window = orchestrator_window
            if ORCHESTRATOR_MODEL.lower() == "deepseek":
                active_func = send_and_extract_deepseek
            else:
                active_func = send_and_extract_chatgpt

        if active_func is None or active_window is None:
            raise Exception("No active tab available for routing request.")

        extracted_data = await active_func(
            prompt_to_send, files=req.files, target_window=active_window
        )

        # 📸 --- Vision Cleanup Loop ---
        for tmp_file in temp_files_to_cleanup:
            try:
                os.remove(tmp_file)
            except Exception:
                pass
        # 📸 ----------------------------

        # Extract markdown text from response
        md_text = extracted_data.get("formatted_markdown", "")

        # 🚀 INTERNAL AUTO-RETRY LOGIC 🚀
        # retry_needed = False
        # retry_prompt = ""

        # # Agar System Error nahi hai toh sirf basic XML structure check karo
        # if not extracted_data.get("error"):
            
        #     # Bas check kar rahe hain ki text mein '<' aur '>' dono hain ya nahi.
        #     if "<" not in md_text or ">" not in md_text:
        #         retry_needed = True
        #         retry_prompt = "[CRITICAL] Your response is entirely missing XML brackets. Please wrap your response in valid XML tags."

        #     if retry_needed:
        #         print(f"🛡️ Format missed! Triggering Internal Auto-Retry to fix it silently...")
        #         # 🚀 Yahan hum successfully wapas call kar rahe hain (Jo pichle code me miss ho gaya tha)
        #         extracted_data = await active_func(
        #             retry_prompt, files=None, target_window=active_window
        #         )
        #         md_text = extracted_data.get("formatted_markdown", "")
        #         print("✅ Internal auto-retry completed! Sending polished response to Cline.")
        # # 🚀 END INTERNAL AUTO-RETRY 🚀
        # Let Roo/Cline handle XML verification natively.

        req_id = f"chatcmpl-{uuid.uuid4().hex}"
        created_time = int(time.time())

        # 🚀 STREAMING FIX: Just stream the raw text exactly like manual_cline_server.py!
        if getattr(req, "stream", False):
            async def generate():
                reply_text = md_text or ""
                chunk_size = 16

                for i in range(0, len(reply_text), chunk_size):
                    text_part = reply_text[i : i + chunk_size]
                    chunk = {
                        "id": req_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": req.model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": text_part},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    await asyncio.sleep(0.01)

                stop_chunk = {
                    "id": req_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": req.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop",
                        }
                    ],
                }
                yield f"data: {json.dumps(stop_chunk)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(generate(), media_type="text/event-stream")

        # 🚀 STATIC JSON RETURN
        return {
            "id": req_id,
            "object": "chat.completion",
            "created": created_time,
            "model": req.model,
            "usage": {
                "prompt_tokens": len(prompt_to_send) // 4,
                "completion_tokens": len(md_text) // 4,
                "total_tokens": (len(prompt_to_send) + len(md_text)) // 4,
            },
            "choices": [
                {
                    "index": 0, 
                    "message": {"role": "assistant", "content": md_text}, 
                    "finish_reason": "stop"
                }
            ],
        }
    except Exception as e:
        import traceback
        print("❌ SERVER FATAL ERROR in openai_mock_api:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# --- 🤖 INTERNAL AGENT-TO-AGENT API 🤖 ---
# --- 🤖 INTERNAL AGENT-TO-AGENT API 🤖 ---
class AgentQuery(BaseModel):
    agent: str  # e.g., "agent-chatgpt-2", "agent-deepseek-1", or just "chatgpt"
    prompt: str
    files: Optional[List[str]] = None  # 🚀 FIX 1: Ab orchestrator yahan seedha file paths bhej sakta hai

@app.post("/v1/agent_chat")
async def agent_chat_api(query: AgentQuery):
    try:
        target_agent = query.agent.lower()
        prompt_to_send = query.prompt.strip()
        files_to_send = query.files  # 🚀 FIX 2: Files extract kar li
        
        print(f"🤖 AGENT DELEGATION: Orchestrator asked '{target_agent}' for help!")
        if files_to_send:
            print(f"📎 Included attachments: {files_to_send}")
        
        # Check explicitly for Jina Agent
        if target_agent == "agent-jina" or target_agent == "jina":
            extracted_data = await fetch_from_jina(prompt_to_send)
        # Check if Orchestrator called a specific agent by exact ID
        elif target_agent in agents_registry:
            active_window = agents_registry[target_agent]
            if "chatgpt" in target_agent:
                extracted_data = await send_and_extract_chatgpt(prompt_to_send, files=files_to_send, target_window=active_window)
            elif "gemini" in target_agent:
                extracted_data = await send_and_extract_gemini(prompt_to_send, files=files_to_send, target_window=active_window)
            else:
                extracted_data = await send_and_extract_deepseek(prompt_to_send, files=files_to_send, target_window=active_window)
        
        # Fallback to general agents if no specific ID provided
        elif target_agent == "chatgpt":
            extracted_data = await send_and_extract_chatgpt(prompt_to_send, files=files_to_send, target_window=chatgpt_window)
        elif target_agent == "deepseek":
            extracted_data = await send_and_extract_deepseek(prompt_to_send, files=files_to_send, target_window=deepseek_window)
        elif target_agent == "gemini":
            extracted_data = await send_and_extract_gemini(prompt_to_send, files=files_to_send, target_window=gemini_window)
        else:
            return {"error": f"Agent '{target_agent}' not found. Available agents are: {list(agents_registry.keys())}"}
            
        return {"agent": target_agent, "response": extracted_data["formatted_markdown"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# ------------------------------------------
# --- 🚀 LAUNCH NEW AGENT API 🚀 ---
class LaunchQuery(BaseModel):
    agent_type: str  # "chatgpt" or "deepseek"

@app.post("/v1/launch_agent")
async def launch_agent_api(query: LaunchQuery):
    try:
        agent_type = query.agent_type.lower()
        print(f"🐣 Spawning new {agent_type.upper()} agent tab...")
        
        # Async lock taaki browser crash na ho
        async with action_lock:
            driver.switch_to.new_window("tab")
            if agent_type == "chatgpt":
                driver.get("https://chatgpt.com/")
            elif agent_type == "deepseek":
                driver.get("https://chat.deepseek.com/")
            elif agent_type == "gemini": driver.get("https://gemini.google.com/app") # 🚀 Spawn Gemini
            else:
                return {"error": "Invalid agent_type. Use 'Chatgpt','Deepseek' or 'Gemini'."}
            
            # Wait for page to load
            await asyncio.sleep(5)
            
            # Re-scan tabs to register the new agent
            update_agents_registry()
            
        return {"status": "success", "message": f"New {agent_type} agent launched successfully!", "available_agents": list(agents_registry.keys())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# ----------------------------------
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
                    "quantization_level": "Q4_0",
                },
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
    async with action_lock:
        try:
            latest_msg = req.messages[-1]
            content = (
                latest_msg.content
                if isinstance(latest_msg.content, str)
                else str(latest_msg.content)
            )
            clean_prompt = content.strip()
            # deemoji_prompt = emoji.demojize(clean_prompt)
            prompt_to_send = clean_prompt  # Use clean_prompt directly, no de-emojizing

            print(f"🕵️‍♀️ Ollama Disguise: Forwarding to ChatGPT browser...")
            extracted_data = await send_and_extract_chatgpt(prompt_to_send)

            return {
                "model": req.model,
                "created_at": datetime.now().isoformat(),
                "message": {
                    "role": "assistant",
                    "content": extracted_data["formatted_markdown"],
                },
                "done": True,
                "done_reason": "stop",
            }
        except Exception as e:
            print(f"Ollama endpoint error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("ai_scraper:app", host="0.0.0.0", port=8000, reload=False)
