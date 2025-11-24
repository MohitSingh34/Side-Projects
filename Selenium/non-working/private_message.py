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

# --- Regex for Private Commands ---
PRIVATE_COMMAND_FIND_REGEX = re.compile(r"(\[.*?\])", re.DOTALL)
PRIVATE_COMMAND_PARSE_REGEX = re.compile(
    r"\[\s*type\s*:\s*private message\s*;\s*for\s*:\s*(Deepseek|ChatGPT)\s*;\s*message\s*:\s*{(.*?)}\s*\]",
    re.IGNORECASE | re.DOTALL
)
# --- Regex for Group Chat Trigger ---
CLIPBOARD_REGEX = re.compile(r"\[ Conversation till (Deepseek|ChatGPT|Gemini)'s last message : (.*) \]", re.DOTALL)


# --- Helper Function: Find and switch (WITH DELAY) ---
def switch_to_ai_tab(driver, target_ai_name):
    """ Tries to find and switch to the tab of the target AI. Returns True if successful, False otherwise. """
    original_handle = None
    try:
        time.sleep(0.5) # Give browser a moment
        
        try:
            original_handle = driver.current_window_handle
            all_handles = driver.window_handles
        except NoSuchWindowException:
             print("DEBUG: Browser window closed.")
             return False # Browser closed
             
        if not all_handles or len(all_handles) < 1:
             print("DEBUG: No window handles found.")
             return False

        for i, handle in enumerate(all_handles):
            try:
                current_handles_check = driver.window_handles
                if handle not in current_handles_check:
                    continue
            except NoSuchWindowException:
                return False 

            try:
                driver.switch_to.window(handle)
                time.sleep(0.2)
                current_url = driver.current_url.lower()

                is_target = False
                if target_ai_name == "ChatGPT" and ("chatgpt.com" in current_url or "chat.openai.com" in current_url):
                    is_target = True
                elif target_ai_name == "Deepseek" and "deepseek.com" in current_url:
                    is_target = True
                elif target_ai_name == "Gemini" and "gemini.google.com" in current_url:
                    is_target = True

                if is_target:
                    return True # Return immediately once found

            except NoSuchWindowException:
                continue 
            except Exception as switch_err:
                # print(f"DEBUG: Error switching to/checking handle {handle}: {switch_err}") # Less verbose
                continue 

        if original_handle and original_handle in driver.window_handles:
             driver.switch_to.window(original_handle)
        return False

    except NoSuchWindowException:
        print(f"[ERROR] Original browser window closed while trying to switch tabs.")
        return False
    except Exception as e:
        # print(f"DEBUG: Unexpected error in switch_to_ai_tab: {e}") # Too verbose
        try:
           if original_handle and original_handle in driver.window_handles:
                driver.switch_to.window(original_handle)
        except: pass
        return False

# --- Helper Function: Send message ---
def send_message_on_current_tab(driver, target_ai_name, message):
    """ Sends message on the currently active tab """
    print(f"DEBUG: Sending message to {target_ai_name}...")
    input_selector, send_selector, use_enter = None, None, False

    if target_ai_name == "ChatGPT":
        input_selector, send_selector = CHATGPT_INPUT_SELECTOR, CHATGPT_SEND_BUTTON_SELECTOR
    elif target_ai_name == "Deepseek":
        input_selector, use_enter = DEEPSEEK_INPUT_SELECTOR, True
    elif target_ai_name == "Gemini":
        input_selector, send_selector = GEMINI_INPUT_SELECTOR, GEMINI_SEND_BUTTON_SELECTOR
    else:
        return False

    try:
        if not message or message.isspace():
            print("[INFO] Message khali tha, sending skip kiya.")
            return False

        pyperclip.copy(message)
        textarea = driver.find_element(*input_selector)
        textarea.click(); time.sleep(0.1)
        textarea.send_keys(Keys.CONTROL, 'a'); time.sleep(0.1)
        textarea.send_keys(Keys.DELETE); time.sleep(0.1)
        textarea.send_keys(Keys.CONTROL, 'v')
        print(f"{target_ai_name} mein message paste kiya...")

        if use_enter:
            time.sleep(0.6); textarea.send_keys(Keys.ENTER)
        elif send_selector:
            time.sleep(0.5); wait = WebDriverWait(driver, 10)
            send_button = wait.until(EC.element_to_be_clickable(send_selector))
            send_button.click()
        
        print(f"DEBUG: Message send successful for {target_ai_name}.")
        return True
    except Exception as e:
        print(f"{target_ai_name} par message bhejte waqt error: {e}")
        return False

# --- Helper Function: Wait for private response (no clipboard copy) ---
def wait_for_private_response(driver, ai_name, potential_dict):
    """
    Waits (BLOCKING) for the AI on the current tab to respond.
    Does NOT copy to clipboard. Returns the response text.
    """
    print(f"[PRIVATE] {ai_name} ke private response ka intezaar hai...")
    start_time = time.time()
    timeout_seconds = 300 # 5 minutes wait max

    while time.time() - start_time < timeout_seconds:
        try:
            is_generating, is_complete_flag = False, False
            if ai_name == "Deepseek":
                try:
                    if driver.find_element(*DEEPSEEK_STOP_SELECTOR).is_displayed(): is_generating = True
                except NoSuchElementException: is_generating = False
            elif ai_name == "ChatGPT":
                try:
                    turns = driver.find_elements(*CHATGPT_TURN_SELECTOR)
                    if turns and turns[-1].find_element(*CHATGPT_COPY_BUTTON_SELECTOR).is_displayed():
                        is_complete_flag = True
                except (NoSuchElementException, StaleElementReferenceException): pass
            elif ai_name == "Gemini":
                 try:
                    if driver.find_element(*GEMINI_STOP_SELECTOR).is_displayed(): is_generating = True
                 except NoSuchElementException: is_generating = False

            if is_generating:
                if ai_name in potential_dict: potential_dict[ai_name] = None
                time.sleep(1); continue
            else:
                current_text_on_page = ""
                copy_now = False 
                
                if ai_name == "Deepseek":
                    try:
                        message_containers = driver.find_elements(By.CSS_SELECTOR, "div[class*='_4f9bf79']")
                        if not message_containers:
                            if ai_name in potential_dict: potential_dict[ai_name] = None
                            time.sleep(1); continue
                        last_container = message_containers[-1]
                        response_element = last_container.find_element(By.XPATH, ".//div[contains(@class, 'ds-markdown')]")
                        current_text_on_page = response_element.text
                    except (NoSuchElementException, StaleElementReferenceException):
                        if ai_name in potential_dict: potential_dict[ai_name] = None
                        time.sleep(1); continue
                    
                    potential_msg_current = potential_dict.get(ai_name)
                    if potential_msg_current is not None and current_text_on_page == potential_msg_current:
                        copy_now = True
                    elif current_text_on_page:
                         potential_dict[ai_name] = current_text_on_page
                         time.sleep(1); continue
                    else:
                        if ai_name in potential_dict: potential_dict[ai_name] = None
                        time.sleep(1); continue

                elif ai_name == "Gemini":
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

                elif ai_name == "ChatGPT":
                    if is_complete_flag:
                        turns = driver.find_elements(*CHATGPT_TURN_SELECTOR)
                        if turns:
                             try:
                                  current_text_on_page = turns[-1].find_element(*CHATGPT_RESPONSE_TEXT_SELECTOR).text
                                  copy_now = True
                             except StaleElementReferenceException: time.sleep(0.5); continue
                    else: time.sleep(1); continue

                if copy_now and current_text_on_page:
                    print(f"✅ Private response {ai_name} se detect hua.")
                    if ai_name in potential_dict: potential_dict[ai_name] = None
                    return current_text_on_page # Return the text
                elif copy_now:
                    if ai_name in potential_dict: potential_dict[ai_name] = None
                    return "" # Return empty string if stable but no text

        except StaleElementReferenceException:
            if ai_name in potential_dict: potential_dict[ai_name] = None
            time.sleep(0.5); continue
        except NoSuchWindowException:
            print(f"[ERROR] Window closed during wait_for_private_response for {ai_name}.")
            return None 
        except Exception as e:
            if ai_name in potential_dict: potential_dict[ai_name] = None
            time.sleep(1); continue

    print(f"[TIMEOUT] {ai_name} se private response {timeout_seconds} seconds mein nahi mila.")
    return None # Return None on timeout


# --- Helper Function: Wait for response and copy (Public) ---
def wait_and_copy_response(driver, ai_name, last_copied_dict, potential_dict, processed_private_commands):
    """
    Waits (BLOCKING) for the AI on the current tab to respond.
    For Gemini: Filters out/handles private commands (even while streaming) and copies only public text.
    Returns (True/False for copied)
    """
    print(f"{ai_name} ke public response ka intezaar hai...")
    copied = False
    start_time = time.time()
    timeout_seconds = 300 # 5 minutes wait max

    while time.time() - start_time < timeout_seconds:
        try:
            current_text_on_page = ""
            
            # --- 1. Get Current Text ---
            if ai_name == "Deepseek":
                try:
                    message_containers = driver.find_elements(By.CSS_SELECTOR, "div[class*='_4f9bf79']")
                    if message_containers: current_text_on_page = message_containers[-1].find_element(By.XPATH, ".//div[contains(@class, 'ds-markdown')]").text
                except (NoSuchElementException, StaleElementReferenceException): pass
            elif ai_name == "Gemini":
                try:
                    response_elements = driver.find_elements(*GEMINI_RESPONSE_SELECTOR)
                    if response_elements: current_text_on_page = response_elements[-1].text
                except (NoSuchElementException, StaleElementReferenceException): pass
            elif ai_name == "ChatGPT":
                try:
                    turns = driver.find_elements(*CHATGPT_TURN_SELECTOR)
                    if turns: current_text_on_page = turns[-1].find_element(*CHATGPT_RESPONSE_TEXT_SELECTOR).text
                except (NoSuchElementException, StaleElementReferenceException): pass

            # --- 2. (Gemini ONLY) Stream Private Commands ---
            if ai_name == "Gemini" and current_text_on_page:
                all_commands = set(PRIVATE_COMMAND_FIND_REGEX.findall(current_text_on_page))
                new_commands = all_commands - processed_private_commands["Gemini"]
                if new_commands:
                    print(f"[Streaming] (Active Mode) {len(new_commands)} naye private commands detect hue.")
                    handle_private_commands(driver, list(new_commands), last_copied_dict, potential_dict, processed_private_commands)
                    processed_private_commands["Gemini"].update(new_commands) # Mark as processed

            # --- 3. Check Generation Status ---
            is_generating, is_complete_flag = False, False 
            if ai_name == "Deepseek":
                try:
                    if driver.find_element(*DEEPSEEK_STOP_SELECTOR).is_displayed(): is_generating = True
                except NoSuchElementException: is_generating = False
            elif ai_name == "ChatGPT":
                try:
                    turns = driver.find_elements(*CHATGPT_TURN_SELECTOR)
                    if turns and turns[-1].find_element(*CHATGPT_COPY_BUTTON_SELECTOR).is_displayed(): is_complete_flag = True
                except (NoSuchElementException, StaleElementReferenceException): pass
            elif ai_name == "Gemini":
                 try:
                    if driver.find_element(*GEMINI_STOP_SELECTOR).is_displayed(): is_generating = True
                 except NoSuchElementException: is_generating = False

            if is_generating:
                if ai_name in potential_dict: potential_dict[ai_name] = None
                time.sleep(1); continue # Wait for generation to finish

            # --- 4. Process Public Message (After Generation) ---
            if not is_generating:
                if ai_name == "ChatGPT" and not is_complete_flag:
                    time.sleep(1); continue # Wait for copy button

                # Check for stability
                potential_msg_current = potential_dict.get(ai_name)
                
                if potential_msg_current is not None and current_text_on_page == potential_msg_current:
                    # --- STABLE AND NEW ---
                    public_text = current_text_on_page
                    full_text_for_history = current_text_on_page
                    
                    if ai_name == "Gemini":
                        public_text = PRIVATE_COMMAND_FIND_REGEX.sub('', current_text_on_page).strip()
                    
                    if public_text and public_text != last_copied_dict.get(f"{ai_name}_public", ""):
                        print(f"\n✅ Naya {ai_name} PUBLIC response detect hua! Copying...")
                        final_text = f"{ai_name}: {public_text}"
                        pyperclip.copy(final_text)
                        last_copied_dict[ai_name] = full_text_for_history
                        last_copied_dict[f"{ai_name}_public"] = public_text
                        print("Success! Public response clipboard par copy ho gaya.")
                        copied = True
                    elif public_text == last_copied_dict.get(f"{ai_name}_public", ""):
                        copied = True # Stable but already copied
                        last_copied_dict[ai_name] = full_text_for_history
                    elif not public_text and ai_name == "Gemini":
                        print("[INFO] Gemini se sirf private command mila (Active Mode), public response nahi.")
                        copied = True
                        last_copied_dict[ai_name] = full_text_for_history
                    
                    if ai_name in potential_dict: potential_dict[ai_name] = None
                    return copied # Exit loop
                
                elif current_text_on_page != potential_msg_current:
                     # Still changing or new
                     potential_dict[ai_name] = current_text_on_page
                     time.sleep(1); continue
                elif not current_text_on_page:
                    time.sleep(1); continue

        except StaleElementReferenceException:
            if ai_name in potential_dict: potential_dict[ai_name] = None
            time.sleep(0.5); continue
        except NoSuchWindowException:
            print(f"[ERROR] Window closed during wait_and_copy for {ai_name}.")
            return False
        except Exception as e:
            if ai_name in potential_dict: potential_dict[ai_name] = None
            time.sleep(1); continue

    if not copied:
        print(f"[TIMEOUT] {ai_name} se public response {timeout_seconds} seconds mein nahi mila.")
    return False 


# --- Helper Function: Handle Private Command Loop ---
def handle_private_commands(driver, commands_list, last_copied_dict, potential_dict, processed_private_commands):
    """
    Processes a list of private commands from Gemini.
    """
    print(f"--- 🤖 Private Command Loop Shuru (Total: {len(commands_list)}) ---")
    
    for command_string in commands_list:
        match = PRIVATE_COMMAND_PARSE_REGEX.search(command_string)
        
        if not match:
            print(f"[WARNING] Invalid private command format, ignoring: {command_string[:50]}...")
            continue
            
        target_ai_private = match.group(1).strip()
        message_private = match.group(2).strip()
        
        print(f"--- P-Loop: Command bhej raha hai -> {target_ai_private} ---")
        
        if switch_to_ai_tab(driver, target_ai_private):
            if send_message_on_current_tab(driver, target_ai_private, message_private):
                if target_ai_private in potential_dict: potential_dict[target_ai_private] = None
                
                # We use the blocking wait here, as this is a private loop
                private_response = wait_for_private_response(driver, target_ai_private, potential_dict)
                
                if private_response is not None:
                    print(f"--- P-Loop: Response {target_ai_private} se mila, Admin (Gemini) ko bhej raha hai ---")
                    if switch_to_ai_tab(driver, "Gemini"):
                        response_to_admin = f"[ Private response from {target_ai_private}: {private_response} ]"
                        
                        # Add this response to processed commands *before* sending
                        # to prevent Gemini from re-processing its own feedback loop
                        processed_private_commands["Gemini"].add(response_to_admin)
                        
                        if not send_message_on_current_tab(driver, "Gemini", response_to_admin):
                            print("[ERROR] P-Loop: Admin (Gemini) ko private response bhej nahi paya.")
                    else:
                        print("[ERROR] P-Loop: Admin (Gemini) ka tab nahi mila.")
                else:
                    print(f"[ERROR] P-Loop: {target_ai_private} se private response nahi mila (timeout).")
            else:
                print(f"[ERROR] P-Loop: {target_ai_private} ko private message bhej nahi paya.")
        else:
            print(f"[ERROR] P-Loop: {target_ai_private} ka tab nahi mila.")
            
    print("--- 🤖 Private Command Loop Samapt. Main monitoring chalu. ---")


# --- *** NEW *** Helper Function: Passively check Gemini (Admin) tab ---
def passively_check_admin_tab(driver, ai_name, last_copied_dict, potential_dict, processed_private_commands, last_processed_clipboard_ref):
    """
    NON-BLOCKING check of the Gemini (Admin) tab.
    Handles streaming private commands AND stable public messages.
    """
    if ai_name != "Gemini": return # Failsafe
    
    try:
        current_text_on_page = ""
        
        # --- 1. Get Current Text ---
        try:
            response_elements = driver.find_elements(*GEMINI_RESPONSE_SELECTOR)
            if response_elements:
                current_text_on_page = response_elements[-1].text
        except (NoSuchElementException, StaleElementReferenceException):
            return # No text, do nothing

        if not current_text_on_page:
            return

        # --- 2. Stream Private Commands (Always check) ---
        all_commands = set(PRIVATE_COMMAND_FIND_REGEX.findall(current_text_on_page))
        new_commands = all_commands - processed_private_commands["Gemini"]
        if new_commands:
            print(f"[Streaming] (Passive Mode) {len(new_commands)} naye private commands detect hue.")
            handle_private_commands(driver, list(new_commands), last_copied_dict, potential_dict, processed_private_commands)
            processed_private_commands["Gemini"].update(new_commands) # Mark as processed

        # --- 3. Check Generation Status ---
        is_generating = False
        try:
            if driver.find_element(*GEMINI_STOP_SELECTOR).is_displayed(): is_generating = True
        except NoSuchElementException: 
            is_generating = False

        if is_generating:
            if ai_name in potential_dict: potential_dict[ai_name] = None # Reset potential
            return # Exit, streaming commands already handled

        # --- 4. Process Public Message (Only if stable) ---
        if current_text_on_page == last_copied_dict.get(ai_name, ""):
            return # Already processed this full text

        potential_msg_current = potential_dict.get(ai_name)

        if potential_msg_current is not None and current_text_on_page == potential_msg_current:
            # --- STABLE AND NEW ---
            print(f"[Passive] Naya {ai_name} response stable hua.")
            
            public_text = PRIVATE_COMMAND_FIND_REGEX.sub('', current_text_on_page).strip()
            full_text_for_history = current_text_on_page

            last_copied_dict[ai_name] = full_text_for_history
            potential_dict[ai_name] = None # Reset potential
            
            if public_text:
                print(f"✅ [Passive] Public response {ai_name} se copy kar raha hai...")
                final_text = f"{ai_name}: {public_text}"
                pyperclip.copy(final_text)
                last_copied_dict[f"{ai_name}_public"] = public_text
                last_processed_clipboard_ref['value'] = final_text
            
        elif current_text_on_page != potential_msg_current:
            # --- STILL CHANGING ---
            potential_dict[ai_name] = current_text_on_page # Update potential
            
    except (StaleElementReferenceException, NoSuchWindowException):
        pass # Ignore, will retry
    except Exception as e:
        print(f"[ERROR] [Passive] {ai_name} ko check karte waqt error: {e}")
        pass


# --- Main script ---
print("--- Auto-Copy & Command Smart Scraper (Admin-Focused Mode) ---")
print("Band karne ke liye terminal mein Ctrl+C dabayein.")

chrome_options = uc.ChromeOptions()
profile_path = os.path.join(os.path.expanduser('~'), 'chrome-profile-uc')
chrome_options.add_argument(f"--user-data-dir={profile_path}")

try:
    driver = uc.Chrome(options=chrome_options)
    print("Successfully started! Aap pehle se logged in hone chahiye.")
    window_width, window_height = 273, 768
    print(f"Browser window ko set kar raha hoon: {window_width}x{window_height} at (0,0)")
    driver.set_window_size(window_width, window_height)
    driver.set_window_position(0, 0)
except Exception as e:
    print(f"\n[ERROR] Chrome shuru nahi ho paya: {e}"); exit()

monitor_clipboard = input("Kya aap AI-to-AI group chat ke liye clipboard monitoring shuru karna chahte hain? (y/n): ")
if monitor_clipboard.lower() == 'n':
    print("\nOK! Script band kar di jayegi."); driver.quit(); exit()
    
print("\n✅ OK! Clipboard monitoring chalu hai (Active Command + Passive Admin Mode).")

# --- *** FIX 1: Add Startup Delay *** ---
print("Browser tabs ko load hone de raha hoon... (5 seconds)")
time.sleep(5)

# Use a dictionary reference to share 'last_processed_clipboard'
last_processed_clipboard_ref = {'value': pyperclip.paste()}

last_copied_message = { 
    "ChatGPT": "", "Deepseek": "", "Gemini": "",
    "ChatGPT_public": "", "Deepseek_public": "", "Gemini_public": "" 
}
potential_message = { "Deepseek": None, "Gemini": None }
# --- *** FIX 2: Add memory for processed commands *** ---
processed_private_commands = {"Gemini": set()}


try:
    while True:
        # --- *** PART 1: ACTIVE COMMAND MODE (HIGH PRIORITY) *** ---
        current_clipboard = pyperclip.paste()
        
        if current_clipboard != last_processed_clipboard_ref['value']:
            match = CLIPBOARD_REGEX.search(current_clipboard)
            if match:
                print(f"\n🤖 Naya Group Chat command (Active Mode) detect hua!")
                target_ai = match.group(1) 
                message_to_send = match.group(2).strip()
                print(f"(Command indicates message should be sent TO {target_ai})")

                if switch_to_ai_tab(driver, target_ai):
                    if send_message_on_current_tab(driver, target_ai, message_to_send):
                        last_processed_clipboard_ref['value'] = message_to_send if message_to_send else current_clipboard
                        
                        # Pass command memory to blocking function
                        copied = wait_and_copy_response(driver, target_ai, last_copied_message, potential_message, processed_private_commands)
                        
                        if copied:
                            new_clipboard_content = pyperclip.paste()
                            if new_clipboard_content != last_processed_clipboard_ref['value']:
                                last_processed_clipboard_ref['value'] = new_clipboard_content
                                print(f"DEBUG: Public response (Active) copy hua.")
                            # Private commands are handled *inside* wait_and_copy_response
                        else:
                            print(f"[ERROR] (Active) {target_ai} se response copy nahi ho paya.")
                            last_processed_clipboard_ref['value'] = current_clipboard
                    else:
                        print(f"[ERROR] (Active) {target_ai} ko message nahi bhej paya.")
                        last_processed_clipboard_ref['value'] = current_clipboard
                else:
                    print(f"[ERROR] (Active) {target_ai} ka tab nahi mila.")
                    last_processed_clipboard_ref['value'] = current_clipboard
                
                time.sleep(1) # Short pause after active command
                continue 
            else:
                last_processed_clipboard_ref['value'] = current_clipboard

        # --- *** PART 2: PASSIVE "ADMIN" MONITORING MODE (LOW PRIORITY) *** ---
        try:
            if switch_to_ai_tab(driver, "Gemini"):
                # Pass all dictionaries to passive checker
                passively_check_admin_tab(driver, "Gemini", 
                                        last_copied_message, 
                                        potential_message, 
                                        processed_private_commands, 
                                        last_processed_clipboard_ref)
            else:
                # print("DEBUG: [Passive] Gemini (Admin) ka tab nahi mila.") # Optional
                pass
        except Exception as e:
            print(f"[ERROR] [Passive] Gemini ko passively check karte waqt error: {e}")
        
        time.sleep(2) # Main loop sleep

except KeyboardInterrupt:
    print("\nScript ko band kiya ja raha hai...")
except Exception as e:
    print(f"\n[UNEXPECTED ERROR] Ek anjaana error hua: {e}")
finally:
    if 'driver' in locals() and driver:
        driver.quit()
    print("Browser band kar diya. Goodbye!")