import time
import pyperclip
import re
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
# Import WebDriverException for auto-restart
from selenium.common.exceptions import NoSuchElementException, NoSuchWindowException, TimeoutException, StaleElementReferenceException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import traceback # For detailed error printing
from datetime import datetime # For timestamps

# --- SELECTORS CONFIGURATION ---
# (Selectors remain the same...)
DEEPSEEK_STOP_SELECTOR = (By.CSS_SELECTOR, "button[data-testid='stop-button']")
DEEPSEEK_RESPONSE_TEXT_SELECTOR = (By.CSS_SELECTOR, "div.ds-markdown")
DEEPSEEK_INPUT_SELECTOR = (By.CSS_SELECTOR, "textarea[placeholder*='Message DeepSeek']")
CHATGPT_TURN_SELECTOR = (By.CSS_SELECTOR, 'article[data-turn="assistant"]')
CHATGPT_COPY_BUTTON_SELECTOR = (By.CSS_SELECTOR, "button[data-testid='copy-turn-action-button']")
CHATGPT_RESPONSE_TEXT_SELECTOR = (By.CSS_SELECTOR, ".markdown")
CHATGPT_INPUT_SELECTOR = (By.ID, "prompt-textarea")
CHATGPT_SEND_BUTTON_SELECTOR = (By.CSS_SELECTOR, "button[data-testid='send-button']")
GEMINI_STOP_SELECTOR = (By.CSS_SELECTOR, 'button.send-button.stop[aria-label="Stop response"]')
GEMINI_RESPONSE_SELECTOR = (By.CSS_SELECTOR, 'message-content .markdown')
GEMINI_INPUT_SELECTOR = (By.CSS_SELECTOR, 'div[role="textbox"][aria-label="Enter a prompt here"]')
GEMINI_SEND_BUTTON_SELECTOR = (By.CSS_SELECTOR, 'button[aria-label="Send message"]')
AISTUDIO_PROJECT_INPUT_SELECTOR = (By.CSS_SELECTOR, 'textarea[placeholder="Make changes, add new features, ask for anything"]')
AISTUDIO_PROJECT_SEND_BUTTON_ENABLED_SELECTOR = (By.CSS_SELECTOR, 'button[aria-label="Send"]:not([aria-disabled="true"]) span.send-icon')
AISTUDIO_PROJECT_SEND_BUTTON_SVG_WORKING_SELECTOR = (By.CSS_SELECTOR, 'button[aria-label="Send"] svg.running-icon')
AISTUDIO_PROJECT_SEND_BUTTON_SPAN_IDLE_SELECTOR = (By.CSS_SELECTOR, 'button[aria-label="Send"] span.send-icon')
AISTUDIO_HOMEPAGE_INPUT_SELECTOR = (By.CSS_SELECTOR, 'textarea[aria-label="Enter a prompt to generate an app"]')
AISTUDIO_HOMEPAGE_RUN_BUTTON_SELECTOR = (By.CSS_SELECTOR, 'ms-run-button button[aria-label="Run"]')
AISTUDIO_HOMEPAGE_RUN_BUTTON_WORKING_SELECTOR = (By.CSS_SELECTOR, 'ms-run-button button[aria-label="send"][disabled]')
AISTUDIO_SAVE_BUTTON_ENABLED_SELECTOR = (By.CSS_SELECTOR, 'button[aria-label="Save app"]:not([aria-disabled="true"])')
AISTUDIO_SAVE_BUTTON_DISABLED_SELECTOR = (By.CSS_SELECTOR, 'button[aria-label="Save app"][aria-disabled="true"]')
AISTUDIO_GITHUB_BUTTON_SELECTOR = (By.CSS_SELECTOR, 'ms-github-trigger-button button[aria-label="Save to GitHub"]')
AISTUDIO_CLOSE_PANEL_SELECTOR = (By.CSS_SELECTOR, 'button[aria-label="Close panel"]')
AISTUDIO_COMMIT_MSG_SELECTOR = (By.CSS_SELECTOR, 'textarea[formcontrolname="message"]')
AISTUDIO_COMMIT_BUTTON_SELECTOR = (By.CSS_SELECTOR, 'button[aria-label="Push latest changes to GitHub"]')
AISTUDIO_CREATE_REPO_NAME_SELECTOR = (By.CSS_SELECTOR, 'input[formcontrolname="name"]')
AISTUDIO_CREATE_REPO_DESC_SELECTOR = (By.CSS_SELECTOR, 'input[formcontrolname="description"]')
AISTUDIO_CREATE_REPO_BUTTON_SELECTOR = (By.CSS_SELECTOR, 'button[aria-label="Create github repository"]')
AISTUDIO_COMMIT_SUCCESS_SELECTOR = (By.XPATH, "//div[contains(@class, 'central-content')]//span[contains(text(), 'No changes to commit')]")


# --- Regex for Private Commands ---
PRIVATE_COMMAND_FIND_REGEX = re.compile(r"(\[.*?\])", re.DOTALL)
PRIVATE_COMMAND_PARSE_REGEX = re.compile(
    r"\[\s*type\s*:\s*private message\s*;\s*for\s*:\s*(Deepseek|ChatGPT|AIStudio)\s*;\s*message\s*:\s*{(.*?)}\s*\]",
    re.IGNORECASE | re.DOTALL
)
# --- Regex for Group Chat Trigger ---
CLIPBOARD_REGEX = re.compile(r"\[ Conversation till (Deepseek|ChatGPT|Gemini)'s last message : (.*) \]", re.DOTALL)


# --- Main script ---
print(f"[{ts()}] --- Auto-Copy & Command Smart Scraper (Admin-Focused Mode) ---")
print(f"[{ts()}] Band karne ke liye terminal mein Ctrl+C dabayein.")

profile_path = os.path.join(os.path.expanduser('~'), 'chrome-profile-uc')
driver = initialize_driver(profile_path) # Initial driver creation

if not driver:
    print(f"[{ts()}] FATAL: Initial driver creation fail hua. Exiting.")
    exit()

monitor_clipboard = input(f"[{ts()}] Kya aap AI-to-AI group chat ke liye clipboard monitoring shuru karna chahte hain? (y/n): ")
if monitor_clipboard.lower() == 'n':
    print(f"[{ts()}] INFO: Script band kar di jayegi.")
    if driver: driver.quit()
    exit()

print(f"[{ts()}] INFO: Clipboard monitoring chalu hai (Active Command + Passive Admin Mode).")
print(f"[{ts()}] INFO: Browser tabs ko load hone de raha hoon... (10 seconds)")
time.sleep(10)

last_processed_clipboard_ref = {'value': pyperclip.paste()}
last_copied_message = {
    "ChatGPT": "", "Deepseek": "", "Gemini": "",
    "ChatGPT_public": "", "Deepseek_public": "", "Gemini_public": ""
}
potential_message = { "Deepseek": None, "Gemini": None }
processed_private_commands = {"Gemini": set()}
loop_counter = 0

try:
    print(f"[{ts()}] INFO: Main loop shuru...")
    while True:
        loop_counter += 1
        # print(f"\n[{ts()}] --- Loop Iteration: {loop_counter} ---") # Less verbose

        try:
            # --- PART 1: ACTIVE COMMAND MODE ---
            # print(f"[{ts()}] DEBUG: Checking clipboard...") # Less verbose
            current_clipboard = pyperclip.paste()

            if current_clipboard != last_processed_clipboard_ref['value']:
                print(f"[{ts()}] DEBUG: Clipboard changed! '{current_clipboard[:30]}...'")
                match = CLIPBOARD_REGEX.search(current_clipboard)
                if match:
                    print(f"[{ts()}] INFO: Naya Group Chat command (Active Mode) detect hua!")
                    target_ai = match.group(1)
                    message_to_send = match.group(2).strip()
                    print(f"[{ts()}] INFO: (Sending TO {target_ai})")

                    if switch_to_ai_tab(driver, target_ai):
                        send_method = send_message_on_current_tab(driver, target_ai, message_to_send)
                        if send_method:
                            last_processed_clipboard_ref['value'] = message_to_send if message_to_send else current_clipboard
                            copied = wait_and_copy_response(driver, target_ai, last_copied_message, potential_message, processed_private_commands)
                            if copied:
                                new_clipboard_content = pyperclip.paste()
                                if new_clipboard_content and new_clipboard_content != last_processed_clipboard_ref['value']:
                                    last_processed_clipboard_ref['value'] = new_clipboard_content
                                    print(f"[{ts()}] DEBUG: Public response (Active) copy hua.")
                            else: print(f"[{ts()}] ERROR: (Active) {target_ai} se response copy nahi ho paya.")
                        else: print(f"[{ts()}] ERROR: (Active) {target_ai} ko message nahi bhej paya.")
                    else: print(f"[{ts()}] ERROR: (Active) {target_ai} ka tab nahi mila.")

                    time.sleep(1)
                    continue
                else:
                    last_processed_clipboard_ref['value'] = current_clipboard

            # --- PART 2: PASSIVE "ADMIN" MONITORING MODE ---
            # print(f"[{ts()}] DEBUG: Entering passive check...") # Less verbose
            switched_passively = switch_to_ai_tab(driver, "Gemini")
            if switched_passively:
                passively_check_admin_tab(driver, "Gemini",
                                        last_copied_message,
                                        potential_message,
                                        processed_private_commands,
                                        last_processed_clipboard_ref)
            # else: print(f"[{ts()}] DEBUG: [Passive] Gemini tab not found.") # Less verbose

        # --- *** NEW: Catch WebDriverException for auto-restart *** ---
        except WebDriverException as wd_error:
            print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print(f"[{ts()}] CRITICAL: WebDriverException pakda gaya (Session lost?): {wd_error}")
            print(f"[{ts()}] INFO: Browser ko restart karne ki koshish...")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            traceback.print_exc()
            
            # Try to quit the old driver instance
            if driver:
                try:
                    driver.quit()
                    print(f"[{ts()}] INFO: Purana driver instance successfully quit kiya.")
                except Exception as quit_e:
                    print(f"[{ts()}] WARNING: Purana driver quit karte waqt error (ignore karega): {quit_e}")
            
            # Wait before restarting
            time.sleep(5) 
            
            # Re-initialize driver
            driver = initialize_driver(profile_path)
            if not driver:
                print(f"[{ts()}] FATAL: Driver restart fail hua. Script band kar raha hai.")
                break # Exit the main loop if restart fails
            else:
                print(f"[{ts()}] INFO: Driver successfully restart hua. Monitoring jaari...")
                print(f"[{ts()}] INFO: Browser tabs ko load hone de raha hoon... (15 seconds)")
                time.sleep(15) # Longer delay after restart
                # Reset states maybe? Or rely on passive check to re-sync
                last_processed_clipboard_ref['value'] = pyperclip.paste() # Re-sync clipboard state
                potential_message = { "Deepseek": None, "Gemini": None } # Reset potential messages
                processed_private_commands = {"Gemini": set()} # Reset processed commands
                continue # Continue to the next loop iteration with the new driver

        except Exception as loop_error:
             print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
             print(f"[{ts()}] ERROR: Loop ke andar unexpected error aaya (Iteration {loop_counter}): {loop_error}")
             print("Detailed Traceback:")
             traceback.print_exc()
             print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
             print(f"[{ts()}] INFO: Thoda pause le raha hoon (10s)...")
             time.sleep(10)

        # Main loop sleep
        time.sleep(2)

except KeyboardInterrupt:
    print(f"\n[{ts()}] INFO: Script ko band kiya ja raha hai (Ctrl+C)...")
except Exception as e:
    print(f"\n[{ts()}] FATAL: Ek anjaana error hua main script level par: {e}")
    traceback.print_exc()
finally:
    if driver:
        try:
            print(f"[{ts()}] INFO: Final cleanup - Browser band kar raha hai...")
            driver.quit()
            print(f"[{ts()}] INFO: Browser band kar diya.")
        except Exception as quit_error:
            print(f"[{ts()}] ERROR: Final cleanup - Browser band karte waqt error: {quit_error}")
    print(f"[{ts()}] Goodbye!")

# --- [NOTE: Paste the UNCHANGED helper functions here again] ---
# def wait_for_private_response(...): ...
# def wait_and_copy_response(...): ...
# def handle_aistudio_command(...): ...
# def handle_private_commands(...): ...
# def passively_check_admin_tab(...): ...