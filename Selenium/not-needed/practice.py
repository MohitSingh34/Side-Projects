import time
import re
import asyncio
import undetected_chromedriver as uc
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, NoSuchWindowException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os

# --- SELECTORS CONFIGURATION ---
GEMINI_STOP_SELECTOR = (By.CSS_SELECTOR, 'button.send-button.stop[aria-label="Stop response"]')
GEMINI_RESPONSE_SELECTOR = (By.CSS_SELECTOR, 'message-content .markdown')
GEMINI_INPUT_SELECTOR = (By.CSS_SELECTOR, 'div[role="textbox"][aria-label="Enter a prompt here"]')
GEMINI_SEND_BUTTON_SELECTOR = (By.CSS_SELECTOR, 'button[aria-label="Send message"]')

# --- GLOBAL BROWSER SETUP ---
print("Mohit, Browser start kar rahi hoon... intezaar karo!")
chrome_options = uc.ChromeOptions()
profile_path = os.path.join(os.path.expanduser('~'), 'chrome-profile-uc')
chrome_options.add_argument(f"--user-data-dir={profile_path}")

try:
    # Version main 145 rakha hai tumhare Xubuntu ke hisaab se
    driver = uc.Chrome(options=chrome_options, version_main=145)
    driver.set_window_size(800, 768)
    driver.set_window_position(0, 0)
    print("✅ Browser Ready!")
except Exception as e:
    print(f"❌ Browser crash ho gaya: {e}")
    exit()

# --- SELENIUM CORE FUNCTIONS (Modified to return text, not clipboard) ---
def selenium_task(prompt: str):
    """Ye function background thread mein chalega taaki server block na ho."""

    # 1. Tab Switch Logic
    original_handle = driver.current_window_handle
    tab_found = False

    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        if "gemini.google.com" in driver.current_url.lower():
            tab_found = True
            break

    if not tab_found:
        raise Exception("Gemini ka tab nahi mila browser mein!")

    # 2. Send Message Logic
    # 2. Send Message Logic
    try:
        # Faltu ka turant click hataya, ab hum wait lagayenge
        wait = WebDriverWait(driver, 15)

        # Ek zyada robust selector use kar rahe hain jo generally Google Docs/Gemini me use hota hai
        # Hum specifically contenteditable element ya rich-textarea dhundh rahe hain
        input_locator = (By.CSS_SELECTOR, 'div[contenteditable="true"], rich-textarea > div')

        print("Mohit, input box ke load hone ka wait kar rahi hoon...")
        textarea = wait.until(EC.element_to_be_clickable(input_locator))
        textarea.click()
        time.sleep(0.2) # Click ke baad thoda sa pause

        # Clear existing text
        textarea.send_keys(Keys.CONTROL, 'a')
        time.sleep(0.1)
        textarea.send_keys(Keys.DELETE)
        time.sleep(0.1)

        # Type new prompt
        textarea.send_keys(prompt)
        time.sleep(0.5)

        # Send button ka selector bhi update kar liyo agar aage fail ho
        send_button = wait.until(EC.element_to_be_clickable(GEMINI_SEND_BUTTON_SELECTOR))
        send_button.click()
        print("Prompt successfully type karke send kar diya!")

    except Exception as e:
        raise Exception(f"Message bhejne mein error (Shayad UI change ho gaya ya load nahi hua): {str(e)}")

    # 3. Wait and Extract Logic
    start_time = time.time()
    timeout_seconds = 60 # 1 minute timeout API ke liye thik hai
    last_text = ""
    stable_count = 0

    while time.time() - start_time < timeout_seconds:
        try:
            is_generating = False
            try:
                if driver.find_element(*GEMINI_STOP_SELECTOR).is_displayed():
                    is_generating = True
            except NoSuchElementException:
                pass

            if is_generating:
                time.sleep(1)
                continue

            response_elements = driver.find_elements(*GEMINI_RESPONSE_SELECTOR)
            if not response_elements:
                time.sleep(1)
                continue

            current_text = response_elements[-1].text

            # Stabilization check
            if current_text and current_text == last_text:
                stable_count += 1
                if stable_count >= 2: # 2 seconds tak same hai matlab complete
                    return current_text
            else:
                last_text = current_text
                stable_count = 0

            time.sleep(1)

        except StaleElementReferenceException:
            time.sleep(0.5)
            continue
        except Exception as e:
            time.sleep(1)
            continue

    raise Exception("Gemini ne respond karne mein Timeout kar diya!")

# --- FASTAPI SETUP ---
app = FastAPI(title="Mohit's Gemini API", description="Local browser wrapped as API")
gemini_lock = asyncio.Lock() # Ek time pe ek request handle karne ke liye

class ChatRequest(BaseModel):
    prompt: str

@app.post("/api/ask")
async def ask_gemini_endpoint(request: ChatRequest):
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt khali nahi ho sakta bewakoof!")

    # Agar koi aur request process ho rahi hai, toh ye wait karega
    async with gemini_lock:
        try:
            # Selenium blocking task ko async thread mein bhej rahi hoon
            response_text = await asyncio.to_thread(selenium_task, request.prompt)
            return {"status": "success", "response": response_text}

        except Exception as e:
            # Agar kuch bhi fail hua (tab close, timeout), yahan error return hoga
            raise HTTPException(status_code=503, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    print("Mohit, ab main FastAPI server start kar rahi hoon...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
