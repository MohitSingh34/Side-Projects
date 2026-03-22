import time
import pyperclip
import re
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, NoSuchWindowException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os

# --- SELECTORS CONFIGURATION ---
# (Selectors remain the same)
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


# --- Helper Function: Find and switch (WITH DELAY) ---
def switch_to_ai_tab(driver, target_ai_name):
    """ Tries to find and switch to the tab of the target AI. Returns True if successful, False otherwise. """
    print(f"DEBUG: Trying to find tab for {target_ai_name}...")
    original_handle = None
    found_tab = False
    try:
        # --- ADDED DELAY ---
        time.sleep(0.5) # Give browser a moment before getting handles
        # --- END DELAY ---

        original_handle = driver.current_window_handle
        all_handles = driver.window_handles
        print(f"DEBUG: Current handles: {all_handles}")

        if not all_handles or len(all_handles) < 1:
             print("DEBUG: No window handles found.")
             return False

        for i, handle in enumerate(all_handles):
            # Check if handle is still valid before switching
            # Sometimes handles list might become stale immediately
            try:
                current_handles_check = driver.window_handles
                if handle not in current_handles_check:
                    print(f"DEBUG: Handle {handle} no longer valid (stale list?), skipping.")
                    continue
            except NoSuchWindowException: # Could happen if original_handle window closed
                print("DEBUG: Window closed while checking handles list.")
                return False # Exit function if browser seems closed

            print(f"DEBUG: Checking handle {i+1}/{len(all_handles)}: {handle}")
            try:
                driver.switch_to.window(handle)
                # Add another small delay after switching before getting URL
                time.sleep(0.2)
                current_url = driver.current_url.lower()
                print(f"DEBUG: Switched to handle {handle}, URL: {current_url}")

                # Check if this is the target tab
                is_target = False
                if target_ai_name == "ChatGPT" and ("chatgpt.com" in current_url or "chat.openai.com" in current_url):
                    is_target = True
                elif target_ai_name == "Deepseek" and "deepseek.com" in current_url:
                    is_target = True
                elif target_ai_name == "Gemini" and "gemini.google.com" in current_url:
                    is_target = True

                if is_target:
                    print(f"DEBUG: Found target tab for {target_ai_name}!")
                    found_tab = True
                    return True # Return immediately once found

            except NoSuchWindowException:
                print(f"DEBUG: Window {handle} closed during check, skipping.")
                continue # Window closed during check
            except Exception as switch_err:
                print(f"DEBUG: Error switching to/checking handle {handle}: {switch_err}")
                continue # Skip this handle if error occurs

        # If loop finishes without finding the target tab
        print(f"DEBUG: Target tab for {target_ai_name} not found after checking all handles.")
        # Switch back only if original handle still exists
        if original_handle and original_handle in driver.window_handles:
             print("DEBUG: Switching back to original handle.")
             driver.switch_to.window(original_handle)
        return False

    except NoSuchWindowException:
        print(f"[ERROR] Original browser window closed while trying to switch tabs.")
        return False
    except Exception as e:
        print(f"DEBUG: Unexpected error in switch_to_ai_tab: {e}")
        try:
           if original_handle and original_handle in driver.window_handles:
                driver.switch_to.window(original_handle)
        except:
           pass
        return False

# --- Helper Function: Send message ---
# (send_message_on_current_tab function remains the same)
def send_message_on_current_tab(driver, target_ai_name, message):
    """ Sends message on the currently active tab """
    print(f"DEBUG: Attempting to send message to {target_ai_name} on current tab...") # DEBUG
    input_selector = None
    send_selector = None
    use_enter = False

    if target_ai_name == "ChatGPT":
        input_selector = CHATGPT_INPUT_SELECTOR
        send_selector = CHATGPT_SEND_BUTTON_SELECTOR
    elif target_ai_name == "Deepseek":
        input_selector = DEEPSEEK_INPUT_SELECTOR
        use_enter = True
    elif target_ai_name == "Gemini":
        input_selector = GEMINI_INPUT_SELECTOR
        send_selector = GEMINI_SEND_BUTTON_SELECTOR
    else:
        print(f"DEBUG: Unknown AI '{target_ai_name}' in send_message_on_current_tab.") # DEBUG
        return False # Unknown AI

    try:
        if not message or message.isspace():
            print("[INFO] Clipboard message khali tha, sending skip kiya.")
            return False # Indicate not sent, but processed

        # It's safer to copy to clipboard *just before* pasting
        pyperclip.copy(message)
        # print("Message clipboard par copy ho gaya hai.") # Less verbose

        textarea = driver.find_element(*input_selector)
        textarea.click(); time.sleep(0.1)

        # Clear using Keyboard Shortcuts
        textarea.send_keys(Keys.CONTROL, 'a'); time.sleep(0.1)
        textarea.send_keys(Keys.DELETE); time.sleep(0.1)
        # print(f"{target_ai_name} input field clear kiya (Ctrl+A, Del).") # Less verbose

        # Paste the new message
        textarea.send_keys(Keys.CONTROL, 'v')
        print(f"{target_ai_name} mein message paste kiya...")

        # Send the message
        if use_enter:
            time.sleep(0.6)
            textarea.send_keys(Keys.ENTER)
            print(f"{target_ai_name} par Enter press kiya.")
        elif send_selector:
            time.sleep(0.5) # Wait for send button to enable after paste
            wait = WebDriverWait(driver, 10)
            send_button = wait.until(EC.element_to_be_clickable(send_selector))
            # Optional: Scroll button into view if needed
            # driver.execute_script("arguments[0].scrollIntoView(true);", send_button)
            # time.sleep(0.2)
            send_button.click()
            print(f"{target_ai_name} send button click kiya.")
        print(f"DEBUG: Message send attempt successful for {target_ai_name}.") # DEBUG
        return True

    except Exception as e:
        print(f"{target_ai_name} par message bhejte waqt error: {e}")
        return False

# --- Helper Function: Wait for response and copy ---
# (wait_and_copy_response function remains the same)
# --- Helper Function: Wait for response and copy (stays on current tab) ---
def wait_and_copy_response(driver, ai_name, last_copied_dict, potential_dict):
    """ Waits for the AI on the current tab to respond and copies it """
    print(f"{ai_name} ke response ka intezaar hai...")
    copied = False
    potential_msg = potential_dict.get(ai_name)
    start_time = time.time()
    timeout_seconds = 300 # 5 minutes wait max

    while time.time() - start_time < timeout_seconds:
        try:
            is_generating = False
            is_complete_flag = False # For ChatGPT completion signal

            # --- Check Generation Status ---
            if ai_name == "Deepseek":
                try:
                    if driver.find_element(*DEEPSEEK_STOP_SELECTOR).is_displayed(): is_generating = True
                except NoSuchElementException: is_generating = False
            elif ai_name == "ChatGPT":
                try:
                    turns = driver.find_elements(*CHATGPT_TURN_SELECTOR)
                    # Check if the last turn exists and has a visible copy button
                    if turns and turns[-1].find_element(*CHATGPT_COPY_BUTTON_SELECTOR).is_displayed():
                        is_complete_flag = True
                except (NoSuchElementException, StaleElementReferenceException): pass # Ignore if elements aren't ready/stable
            elif ai_name == "Gemini":
                 try:
                    if driver.find_element(*GEMINI_STOP_SELECTOR).is_displayed(): is_generating = True
                 except NoSuchElementException: is_generating = False

            # --- Process Based on Status ---
            if is_generating:
                if ai_name in potential_dict: potential_dict[ai_name] = None # Reset potential message if still generating
                time.sleep(1) # Check frequently
                continue
            else:
                 # --- Try to get text and stabilize ---
                current_text_on_page = ""
                copy_now = False

                if ai_name == "Deepseek":
                    # --- REFINED LOGIC FOR DEEPSEEK ---
                    try:
                        # 1. Find all message containers (divs with class starting with '_4f9bf79')
                        message_containers = driver.find_elements(By.CSS_SELECTOR, "div[class*='_4f9bf79']")
                        if not message_containers:
                            if ai_name in potential_dict: potential_dict[ai_name] = None
                            time.sleep(1); continue # No message containers found yet

                        # 2. Get the *last* message container
                        last_container = message_containers[-1]

                        # 3. Find the text element *within* the last container
                        # Use './/' in XPath to search within the current element context
                        response_element = last_container.find_element(By.XPATH, ".//div[contains(@class, 'ds-markdown')]")
                        current_text_on_page = response_element.text
                    except (NoSuchElementException, StaleElementReferenceException):
                        # If structure changed or element not found in last container, reset and retry
                        if ai_name in potential_dict: potential_dict[ai_name] = None
                        time.sleep(1); continue
                    # --- END OF REFINED LOGIC ---

                    # Now perform stabilization check
                    potential_msg_current = potential_dict.get(ai_name)
                    if potential_msg_current is not None and current_text_on_page == potential_msg_current:
                        copy_now = True
                    elif current_text_on_page:
                         potential_dict[ai_name] = current_text_on_page # Update potential message
                         time.sleep(1); continue # Wait for next check to confirm stability
                    else: # No text found in the last container
                        if ai_name in potential_dict: potential_dict[ai_name] = None
                        time.sleep(1); continue

                elif ai_name == "Gemini": # Gemini stabilization logic
                    selector = GEMINI_RESPONSE_SELECTOR
                    response_elements = driver.find_elements(*selector)
                    if not response_elements:
                        if ai_name in potential_dict: potential_dict[ai_name] = None
                        time.sleep(1); continue
                    current_text_on_page = response_elements[-1].text
                    potential_msg_current = potential_dict.get(ai_name)
                    if potential_msg_current is not None and current_text_on_page == potential_msg_current:
                        copy_now = True
                    elif current_text_on_page:
                         potential_dict[ai_name] = current_text_on_page
                         time.sleep(1); continue
                    else:
                        if ai_name in potential_dict: potential_dict[ai_name] = None
                        time.sleep(1); continue

                elif ai_name == "ChatGPT": # ChatGPT completion logic
                    if is_complete_flag:
                        turns = driver.find_elements(*CHATGPT_TURN_SELECTOR)
                        if turns:
                             try:
                                  current_text_on_page = turns[-1].find_element(*CHATGPT_RESPONSE_TEXT_SELECTOR).text
                                  copy_now = True
                             except StaleElementReferenceException: time.sleep(0.5); continue
                    else: time.sleep(1); continue

                # --- Perform Copy Action ---
                if copy_now and current_text_on_page and current_text_on_page != last_copied_dict[ai_name]:
                    print(f"\n✅ Naya {ai_name} response detect hua {'(stable)' if ai_name != 'ChatGPT' else ''}! Copying...")
                    final_text = f"{ai_name}: {current_text_on_page}"
                    pyperclip.copy(final_text)
                    last_copied_dict[ai_name] = current_text_on_page # Update history
                    if ai_name in potential_dict: potential_dict[ai_name] = None # Reset potential message after successful copy
                    print("Success! Clipboard par copy ho gaya.")
                    copied = True
                    break # Exit wait loop after successful copy
                elif copy_now and current_text_on_page == last_copied_dict[ai_name]:
                     # Response is stable but already copied
                     if ai_name in potential_dict: potential_dict[ai_name] = None # Reset potential message
                     copied = True # Consider it done for this cycle
                     break # Exit wait loop

        except StaleElementReferenceException:
            if ai_name in potential_dict: potential_dict[ai_name] = None # Reset on stale element
            time.sleep(0.5)
            continue
        except NoSuchWindowException:
            print(f"[ERROR] Window closed during wait_and_copy for {ai_name}.")
            break # Exit loop if window is closed
        except Exception as e:
            # print(f"Error during wait_and_copy ({ai_name}): {e}") # Debug
            if ai_name in potential_dict: potential_dict[ai_name] = None
            time.sleep(1)
            continue

    if not copied:
        print(f"[TIMEOUT] {ai_name} se response {timeout_seconds} seconds mein nahi mila.")
    return copied

# --- Main script ---
# (Rest of the script setup is the same...)
print("--- Auto-Copy & Command Smart Scraper (Focused Monitoring) ---")
print("Band karne ke liye terminal mein Ctrl+C dabayein.")

chrome_options = uc.ChromeOptions()
profile_path = os.path.join(os.path.expanduser('~'), 'chrome-profile-uc')
chrome_options.add_argument(f"--user-data-dir={profile_path}")

try:
    driver = uc.Chrome(options=chrome_options)
    print("Successfully started! Aap pehle se logged in hone chahiye.")
    window_width = 273
    window_height = 768
    print(f"Browser window ko set kar raha hoon: {window_width}x{window_height} at (0,0)")
    driver.set_window_size(window_width, window_height)
    driver.set_window_position(0, 0)
except Exception as e:
    print(f"\n[ERROR] Chrome shuru nahi ho paya: {e}")
    exit()

monitor_clipboard = input("Kya aap AI-to-AI group chat ke liye clipboard monitoring shuru karna chahte hain? (y/n): ")
if monitor_clipboard.lower() == 'y':
    print("\n✅ OK! Clipboard monitoring chalu hai.")
    clipboard_regex = re.compile(r"\[ Conversation till (Deepseek|ChatGPT|Gemini)'s last message : (.*) \]", re.DOTALL)
    last_processed_clipboard = pyperclip.paste()
else:
    print("\nOK! Script band kar di jayegi kyunki group chat mode 'n' select kiya gaya.")
    driver.quit()
    exit()

last_copied_message = { "ChatGPT": "", "Deepseek": "", "Gemini": "" }
potential_message = { "Deepseek": None, "Gemini": None }

try:
    while True:
        # --- Main Task: Monitor Clipboard Only ---
        current_clipboard = pyperclip.paste()

        if current_clipboard != last_processed_clipboard:
            match = clipboard_regex.search(current_clipboard)
            if match:
                print(f"\n🤖 Naya Group Chat command clipboard par detect hua!")
                target_ai = match.group(1) # The AI mentioned IS the target
                message_to_send = match.group(2).strip()
                print(f"(Command indicates message should be sent TO {target_ai})")

                # --- Action Sequence ---
                print("DEBUG: Calling switch_to_ai_tab...")
                if switch_to_ai_tab(driver, target_ai):
                    print(f"DEBUG: switch_to_ai_tab succeeded for {target_ai}. Calling send_message_on_current_tab...")
                    if send_message_on_current_tab(driver, target_ai, message_to_send):
                        last_processed_clipboard = message_to_send if message_to_send else current_clipboard
                        print(f"Message safalta se {target_ai} ko bhej diya gaya.")
                        print(f"DEBUG: Calling wait_and_copy_response for {target_ai}...")
                        if wait_and_copy_response(driver, target_ai, last_copied_message, potential_message):
                            last_processed_clipboard = pyperclip.paste()
                            print(f"DEBUG: wait_and_copy_response succeeded for {target_ai}.")
                        else:
                            print(f"[ERROR] {target_ai} se response copy nahi ho paya.")
                            last_processed_clipboard = current_clipboard
                    else:
                        print(f"[ERROR] {target_ai} ko message nahi bhej paya.")
                        last_processed_clipboard = current_clipboard
                else:
                    print(f"DEBUG: switch_to_ai_tab failed for {target_ai}.")
                    print(f"[ERROR] {target_ai} ka tab nahi mila.")
                    last_processed_clipboard = current_clipboard
            # else: # Clipboard changed, but not a command
                 # last_processed_clipboard = current_clipboard

        # Check clipboard every 2 seconds
        time.sleep(2)

except KeyboardInterrupt:
    print("\nScript ko band kiya ja raha hai...")
finally:
    # Ensure browser closes and RAM is freed
    if 'driver' in locals() and driver:
        driver.quit()
    print("Browser band kar diya. Goodbye!")