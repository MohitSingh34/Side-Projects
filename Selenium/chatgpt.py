import json
import time
import os
import asyncio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
        options.add_argument("--user-data-dir=/home/mohit/chrome-profile-uc")
        # options.add_argument('--headless')

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
            voice_btn = driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Start Voice']")
            if voice_btn:
                await asyncio.sleep(2)
                return True

            send_btn = driver.find_elements(By.CSS_SELECTOR, "button[data-testid='send-button']")
            if send_btn and not send_btn[0].get_attribute("disabled"):
                await asyncio.sleep(2)
                return True
        except Exception:
            pass
        await asyncio.sleep(2)
    return False

async def send_and_extract(prompt_text: str):
    """Core function to safely send a prompt and extract the output IN PERFECT ORDER"""
    text_area = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div#prompt-textarea"))
    )
    text_area.clear()
    text_area.send_keys(prompt_text)
    await asyncio.sleep(1)

    send_button = driver.find_element(By.CSS_SELECTOR, "button[data-testid='send-button']")
    send_button.click()

    is_done = await wait_for_response_to_complete()
    if not is_done:
        raise Exception("Response generation timed out.")

    messages = driver.find_elements(By.CSS_SELECTOR, "div[data-message-author-role='assistant']")
    latest_message = messages[-1]

    # ✨ NAYA LOGIC: Line by Line extraction maintain karega!
    formatted_markdown = ""
    plain_text_parts = []
    code_blocks = {}

    # Sirf direct children uthayenge taaki order kharab na ho
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
                # Code block ko usi waqt markdown me append kar diya!
                formatted_markdown += f"```{lang}\n{code_content}\n```\n\n"
                code_idx += 1
            except Exception as e:
                continue
        else:
            # Fallback for blockquotes, tables, etc.
            text = el.text
            formatted_markdown += text + "\n\n"
            plain_text_parts.append(text)

    return {
        "plain-text": "\n\n".join(plain_text_parts),
        "code-blocks": code_blocks,
        "formatted_markdown": formatted_markdown # Ye hamari nayi superpower hai!
    }

async def auto_notes_worker():
    """Background task that runs every 5 minutes to process the JSON queue."""
    await asyncio.sleep(15)
    master_prompt_sent = False

    master_prompt = (
        "Act as a strict technical syntax explainer. Don't use custom instructions, follow what I am saying exactly. "
        "I will send queries in the format 'language concept length' (e.g., 'javascript console.log short'). "
        "If length is 'short', provide the standard syntax structure telling how to use each inside property under 10 lines, and a concise explanation. "
        "If length is 'long', provide extensive code snippets showing use-cases, industry do's/dont's, and deep logic."
        "Separate all code blocks properly using standard markdown formatting."
        "Alway write output of code, always, give flowchart if necessary only in long type explanations"
    )

    while True:
        try:
            if os.path.exists(PENDING_JSON_PATH):
                with open(PENDING_JSON_PATH, "r") as f:
                    pending_words = json.load(f)
            else:
                pending_words = []

            if pending_words:
                print(f"\n[Bot] Found {len(pending_words)} pending syntaxes. Processing...")

                async with driver_lock:
                    if not master_prompt_sent:
                        print("[Bot] Sending initial Master Prompt...")
                        await send_and_extract(master_prompt)
                        master_prompt_sent = True
                        await asyncio.sleep(5)

                    for item in pending_words[:]:
                        parts = item.split(" ")
                        lang = parts[0]
                        concept = " ".join(parts[1:])

                        # --- 1. FETCH SHORT VERSION ---
                        print(f"[Bot] Asking ChatGPT for SHORT version: '{item}'")
                        try:
                            resp_short = await send_and_extract(f"{item} short")
                            md_short = f"@de {concept}\n"

                            # ✨ Ab hum direct perfectly ordered markdown use kar rahe hain
                            md_short += resp_short.get("formatted_markdown", "")

                            file_short = os.path.join(NOTES_DIR, f"{lang}-short.md")
                            with open(file_short, "a", encoding="utf-8") as file:
                                file.write(md_short + "\n")

                            print(f"[Bot] ✨ Saved SHORT note for '{concept}'")
                        except Exception as e:
                            print(f"[Bot] Failed SHORT extraction for {item}: {e}")
                            continue

                        print("[Bot] Waiting 10 seconds before asking for LONG version...")
                        await asyncio.sleep(10)

                        # --- 2. FETCH LONG VERSION ---
                        print(f"[Bot] Asking ChatGPT for LONG version: '{item}'")
                        try:
                            resp_long = await send_and_extract(f"{item} long")
                            md_long = f"@de {concept}\n"

                            # ✨ Same magic for long version
                            md_long += resp_long.get("formatted_markdown", "")

                            file_long = os.path.join(NOTES_DIR, f"{lang}-long.md")
                            with open(file_long, "a", encoding="utf-8") as file:
                                file.write(md_long + "\n")

                            print(f"[Bot] ✨ Saved LONG note for '{concept}'")
                        except Exception as e:
                            print(f"[Bot] Failed LONG extraction for {item}: {e}")
                            continue

                        # --- 3. CLEANUP & WAIT ---
                        pending_words.remove(item)
                        with open(PENDING_JSON_PATH, "w") as f:
                            json.dump(pending_words, f, indent=2)

                        print("[Bot] Successfully processed! Waiting 10 seconds before next keyword...")
                        await asyncio.sleep(10)

            else:
                pass

        except Exception as e:
            print(f"[Bot] Loop error: {e}")

        await asyncio.sleep(300)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_driver()
    bot_task = asyncio.create_task(auto_notes_worker())
    yield
    bot_task.cancel()
    global driver
    print("\nCtrl+C detected! Shutting down gracefully...")
    if driver is not None:
        driver.quit()
        print("Chrome driver closed and resources freed safely. Bye!")

app = FastAPI(lifespan=lifespan)

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
    uvicorn.run("chatgpt:app", host="0.0.0.0", port=8000, reload=False)
