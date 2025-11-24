import time
import pyperclip
import re
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, NoSuchWindowException, TimeoutException, StaleElementReferenceException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import traceback
from datetime import datetime
from functools import wraps
import logging

# WORKING : This script is working
# --- 1. LOGGING and CONFIGURATION ---

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] - %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger(__name__) # Define the logger object

# --- General Settings ---
USER_DATA_DIR = "~/chrome-profile-uc"
WINDOW_WIDTH = 273
WINDOW_HEIGHT = 768
STARTUP_DELAY = 10
LOOP_DELAY = 2
RESTART_DELAY = 15

# --- Regex Patterns ---
PRIVATE_COMMAND_FIND_REGEX = re.compile(r"(\[.*?\])", re.DOTALL)
PRIVATE_COMMAND_PARSE_REGEX = re.compile(
    r"^\s*\[\s*type\s*:\s*private message\s*;\s*for\s*:\s*(Deepseek|ChatGPT|AIStudio)\s*;\s*message\s*:\s*{(.*?)}\s*\]\s*$",
    re.IGNORECASE | re.DOTALL
)
CLIPBOARD_REGEX = re.compile(r"\[ Conversation till (Deepseek|ChatGPT|Gemini)'s last message : (.*) \]", re.DOTALL)

# --- AI URLs for Tab Management ---
AI_URLS = {
    "ChatGPT": ["chatgpt.com", "chat.openai.com"],
    "Deepseek": ["deepseek.com"],
    "Gemini": ["gemini.google.com"],
    "AIStudio": ["aistudio.google.com/apps/drive/", "aistudio.google.com/apps"]
}

# --- SELECTORS ---
class Selectors:
    GEMINI_STOP = (By.CSS_SELECTOR, 'button.send-button.stop[aria-label="Stop response"]')
    GEMINI_RESPONSE = (By.CSS_SELECTOR, 'message-content .markdown')
    GEMINI_INPUT = (By.CSS_SELECTOR, 'div[role="textbox"][aria-label="Enter a prompt here"]')
    GEMINI_SEND = (By.CSS_SELECTOR, 'button[aria-label="Send message"]')
    DEEPSEEK_STOP = (By.CSS_SELECTOR, "button[data-testid='stop-button']")
    DEEPSEEK_INPUT = (By.CSS_SELECTOR, "textarea[placeholder*='Message DeepSeek']")
    DEEPSEEK_RESPONSE_CONTAINER = (By.CSS_SELECTOR, "div[class*='_4f9bf79']")
    DEEPSEEK_RESPONSE_TEXT = (By.XPATH, ".//div[contains(@class, 'ds-markdown')]")
    CHATGPT_TURN = (By.CSS_SELECTOR, 'article[data-turn="assistant"]')
    CHATGPT_COPY_BUTTON = (By.CSS_SELECTOR, "button[data-testid='copy-turn-action-button']")
    CHATGPT_RESPONSE_TEXT = (By.CSS_SELECTOR, ".markdown")
    CHATGPT_INPUT = (By.ID, "prompt-textarea")
    CHATGPT_SEND = (By.CSS_SELECTOR, "button[data-testid='send-button']")
    AISTUDIO_PROJECT_INPUT = (By.CSS_SELECTOR, 'textarea[placeholder="Make changes, add new features, ask for anything"]')
    AISTUDIO_PROJECT_SEND_BUTTON_WORKING = (By.CSS_SELECTOR, 'button[aria-label="Send"].running')
    AISTUDIO_PROJECT_SEND_BUTTON_IDLE = (By.CSS_SELECTOR, 'button[aria-label="Send"]:not(.running)')
    AISTUDIO_HOMEPAGE_INPUT = (By.CSS_SELECTOR, 'textarea[aria-label="Enter a prompt to generate an app"]')
    AISTUDIO_HOMEPAGE_RUN_BUTTON_WORKING = (By.CSS_SELECTOR, 'ms-run-button button[aria-label="Run"][disabled]')
    AISTUDIO_HOMEPAGE_RUN_BUTTON_IDLE = (By.CSS_SELECTOR, 'ms-run-button button[aria-label="Run"]:not([disabled])')
    AISTUDIO_SAVE_ENABLED = (By.CSS_SELECTOR, 'button[aria-label="Save app"]:not([aria-disabled="true"])')
    AISTUDIO_SAVE_DISABLED = (By.CSS_SELECTOR, 'button[aria-label="Save app"][aria-disabled="true"]')
    AISTUDIO_GITHUB_BUTTON = (By.CSS_SELECTOR, 'ms-github-trigger-button button[aria-label="Save to GitHub"]')
    AISTUDIO_CLOSE_PANEL = (By.CSS_SELECTOR, 'button[aria-label="Close panel"]')
    AISTUDIO_COMMIT_MSG_INPUT = (By.CSS_SELECTOR, 'textarea[formcontrolname="message"]')
    AISTUDIO_COMMIT_BUTTON = (By.CSS_SELECTOR, 'button[aria-label="Push latest changes to GitHub"]')
    AISTUDIO_CREATE_REPO_NAME_INPUT = (By.CSS_SELECTOR, 'input[formcontrolname="name"]')
    AISTUDIO_CREATE_REPO_DESC_INPUT = (By.CSS_SELECTOR, 'input[formcontrolname="description"]')
    AISTUDIO_CREATE_REPO_BUTTON = (By.CSS_SELECTOR, 'button[aria-label="Create github repository"]')
    AISTUDIO_COMMIT_SUCCESS_MSG = (By.XPATH, "//div[contains(@class, 'central-content')]//span[contains(text(), 'No changes to commit')]")

# --- 2. UTILITY FUNCTIONS and CLASSES ---

def ts():
    """Returns a timestamp string."""
    return datetime.now().strftime("%H:%M:%S")

def retry_operation(operation, max_attempts=3, delay=2, allowed_exceptions=None):
    if allowed_exceptions is None:
        allowed_exceptions = (StaleElementReferenceException, NoSuchElementException, TimeoutException)
    @wraps(operation)
    def wrapper(*args, **kwargs):
        last_exception = None
        for attempt in range(max_attempts):
            try:
                return operation(*args, **kwargs)
            except allowed_exceptions as e:
                last_exception = e
                if attempt < max_attempts - 1:
                    log.warning(f"Attempt {attempt + 1} for '{operation.__name__}' failed: {str(e).splitlines()[0]}. Retrying...")
                    time.sleep(delay)
                else:
                    log.error(f"All {max_attempts} attempts failed for '{operation.__name__}'.")
                    raise last_exception
        return None
    return wrapper

class ClipboardManager:
    @staticmethod
    def safe_copy(text, max_attempts=3):
        for attempt in range(max_attempts):
            try:
                pyperclip.copy(text)
                time.sleep(0.3)
                if pyperclip.paste().strip() == text.strip():
                    log.debug(f"Clipboard copy verified: '{text[:30]}...'")
                    return True
            except Exception as e:
                log.warning(f"Clipboard copy attempt {attempt + 1} failed: {e}")
                time.sleep(1)
        log.error(f"Clipboard copy failed after {max_attempts} attempts.")
        return False

    @staticmethod
    def safe_paste():
        try:
            return pyperclip.paste()
        except Exception as e:
            log.error(f"Clipboard paste failed: {e}")
            return ""

def is_driver_healthy(driver):
    if not driver: return False
    try: _ = driver.current_url; return True
    except WebDriverException: log.warning("Driver health check failed."); return False

# --- 3. STATE MANAGEMENT ---

class AppState:
    def __init__(self):
        self.driver = None
        self.tab_handles = {}
        self.last_processed_clipboard = ClipboardManager.safe_paste()
        self.last_copied_messages = {"ChatGPT": "", "Deepseek": "", "Gemini": ""}
        self.last_copied_messages_public = {"ChatGPT_public": "", "Deepseek_public": "", "Gemini_public": ""}
        self.potential_messages = {"Deepseek": None, "Gemini": None}
        self.processed_private_commands = {"Gemini": set()}

    def reset(self):
        self.last_processed_clipboard = ClipboardManager.safe_paste()
        self.potential_messages = {"Deepseek": None, "Gemini": None}
        self.processed_private_commands = {"Gemini": set()}
        log.info("Application state reset.")

# --- 4. CORE HELPER FUNCTIONS ---

def initialize_driver(profile_path):
    log.info("Initializing Chrome driver...")
    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument(f"--user-data-dir={profile_path}")
    try:
        driver = uc.Chrome(options=chrome_options)
        log.info("Successfully started/restarted driver!")
        log.info(f"Browser window ko set kar raha hoon: {WINDOW_WIDTH}x{WINDOW_HEIGHT} at (0,0)")
        driver.set_window_size(WINDOW_WIDTH, WINDOW_HEIGHT)
        driver.set_window_position(0, 0)
        return driver
    except Exception as e:
        log.critical(f"Chrome driver shuru nahi ho paya: {e}")
        traceback.print_exc()
        return None

def initialize_tab_management(driver, tab_handles):
    log.info("Initializing tab management...")
    tab_handles.clear()
    original_handle = None
    try: original_handle = driver.current_window_handle
    except WebDriverException: log.error("Failed to get current window handle."); return
    all_handles = driver.window_handles
    log.debug(f"Found {len(all_handles)} handles.")
    for handle in all_handles:
        try:
            driver.switch_to.window(handle)
            time.sleep(0.5)
            url = driver.current_url.lower()
            for name, urls in AI_URLS.items():
                if any(u in url for u in urls):
                    tab_handles[name] = handle
                    log.info(f"Found and stored tab for: {name}")
                    break
        except (NoSuchWindowException, WebDriverException): continue
        except Exception as e: log.warning(f"Error checking handle {handle}: {e}")
    try:
        if original_handle and original_handle in driver.window_handles: driver.switch_to.window(original_handle)
        elif tab_handles: driver.switch_to.window(next(iter(tab_handles.values())))
    except Exception as e: log.error(f"Failed to switch back after tab init: {e}")
    log.info(f"Tab management initialized. Found: {list(tab_handles.keys())}")

@retry_operation
def switch_to_ai_tab(driver, target_ai_name, tab_handles):
    if target_ai_name not in tab_handles:
        log.warning(f"Tab handle for '{target_ai_name}' not found. Re-initializing.")
        initialize_tab_management(driver, tab_handles)
        if target_ai_name not in tab_handles:
            log.error(f"Could not find tab for '{target_ai_name}' after re-scan.")
            return False
    driver.switch_to.window(tab_handles[target_ai_name])
    time.sleep(0.5)
    return True

@retry_operation
def send_message(driver, ai_name, message):
    log.debug(f"Sending message to {ai_name}...")
    method_used = None
    if not message or message.isspace(): log.info("Message khali."); return None
    ClipboardManager.safe_copy(message); textarea = None; send_selector = False; use_enter = False; use_ctrl_enter = False

    if ai_name == "AIStudio":
        try:
            textarea = WebDriverWait(driver, 3).until(EC.presence_of_element_located(Selectors.AISTUDIO_PROJECT_INPUT)); send_selector = True
        except TimeoutException:
            try: textarea = WebDriverWait(driver, 3).until(EC.presence_of_element_located(Selectors.AISTUDIO_HOMEPAGE_INPUT)); use_ctrl_enter = True
            except TimeoutException: log.error("AIStudio input box not found."); return None
    elif ai_name == "ChatGPT": textarea = WebDriverWait(driver, 10).until(EC.presence_of_element_located(Selectors.CHATGPT_INPUT)); send_selector = True
    elif ai_name == "Deepseek": textarea = WebDriverWait(driver, 10).until(EC.presence_of_element_located(Selectors.DEEPSEEK_INPUT)); use_enter = True
    elif ai_name == "Gemini": textarea = WebDriverWait(driver, 10).until(EC.presence_of_element_located(Selectors.GEMINI_INPUT)); send_selector = True
    else: return None

    textarea.click(); time.sleep(0.1); textarea.send_keys(Keys.CONTROL, 'a'); time.sleep(0.1); textarea.send_keys(Keys.DELETE); time.sleep(0.1); textarea.send_keys(Keys.CONTROL, 'v'); log.info(f"{ai_name} mein paste kiya.")

    if use_ctrl_enter: time.sleep(0.6); textarea.send_keys(Keys.CONTROL, Keys.ENTER); method_used = 'ctrl_enter'; log.info(f"{ai_name} par Ctrl+Enter.")
    elif use_enter: time.sleep(0.6); textarea.send_keys(Keys.ENTER); method_used = 'enter'; log.info(f"{ai_name} par Enter.")
    elif send_selector:
        time.sleep(0.5); wait = WebDriverWait(driver, 10)
        if ai_name == "AIStudio": send_button_locator = (By.CSS_SELECTOR, 'button[aria-label="Send"]:not(.disabled):not([aria-disabled="true"])')
        elif ai_name == "ChatGPT": send_button_locator = Selectors.CHATGPT_SEND
        elif ai_name == "Gemini": send_button_locator = Selectors.GEMINI_SEND
        else: raise Exception("Send selector logic error")
        send_button_element = wait.until(EC.element_to_be_clickable(send_button_locator)); send_button_element.click(); method_used = 'click'; log.info(f"{ai_name} par 'Send' button click.")
    log.debug(f"Send successful ({method_used})."); return method_used

@retry_operation
def wait_for_private_response(driver, ai_name, state):
    log.info(f"Waiting for private response from {ai_name}..."); start_time = time.time(); timeout_seconds = 300
    potential_dict = state.potential_messages
    while time.time() - start_time < timeout_seconds:
        is_generating, is_complete_flag = False, False
        if ai_name == "Deepseek":
            try: is_generating = driver.find_element(*Selectors.DEEPSEEK_STOP).is_displayed()
            except NoSuchElementException: is_generating = False
        elif ai_name == "ChatGPT":
            try: turns = driver.find_elements(*Selectors.CHATGPT_TURN); is_complete_flag = turns and turns[-1].find_element(*Selectors.CHATGPT_COPY_BUTTON).is_displayed()
            except (NoSuchElementException, StaleElementReferenceException): pass
        if is_generating:
            if ai_name in potential_dict: potential_dict[ai_name] = None; time.sleep(1); continue
        else:
            current_text_on_page = ""; copy_now = False
            if ai_name == "Deepseek":
                try:
                    msgs = driver.find_elements(*Selectors.DEEPSEEK_RESPONSE_CONTAINER);
                    if not msgs:
                        if ai_name in potential_dict: potential_dict[ai_name] = None; time.sleep(1); continue
                    current_text_on_page = msgs[-1].find_element(*Selectors.DEEPSEEK_RESPONSE_TEXT).text
                except (NoSuchElementException, StaleElementReferenceException):
                    if ai_name in potential_dict: potential_dict[ai_name] = None; time.sleep(1); continue
                potential = potential_dict.get(ai_name)
                if potential is not None and current_text_on_page == potential: copy_now = True
                elif current_text_on_page: potential_dict[ai_name] = current_text_on_page; time.sleep(1); continue
                else:
                    if ai_name in potential_dict: potential_dict[ai_name] = None; time.sleep(1); continue
            elif ai_name == "ChatGPT":
                if is_complete_flag:
                    turns = driver.find_elements(*Selectors.CHATGPT_TURN)
                    if turns:
                        try: current_text_on_page = turns[-1].find_element(*Selectors.CHATGPT_RESPONSE_TEXT).text; copy_now = True
                        except StaleElementReferenceException: time.sleep(0.5); continue
                else: time.sleep(1); continue
            if copy_now and current_text_on_page: log.info(f"Private response {ai_name} detect hua."); return current_text_on_page
            elif copy_now: return ""
    log.error(f"Timeout ({timeout_seconds}s) for {ai_name} private response."); return None

@retry_operation
def wait_for_response(driver, ai_name, state): # Renamed for clarity, combines wait and copy
    log.info(f"Waiting for public response from {ai_name}..."); copied = False; start_time = time.time(); timeout_seconds = 300
    potential_dict = state.potential_messages
    last_copied_dict = state.last_copied_messages
    processed_private_commands = state.processed_private_commands

    while time.time() - start_time < timeout_seconds:
        current_text_on_page = ""
        if ai_name == "Deepseek":
            try: msgs = driver.find_elements(*Selectors.DEEPSEEK_RESPONSE_CONTAINER); current_text_on_page = msgs[-1].find_element(*Selectors.DEEPSEEK_RESPONSE_TEXT).text if msgs else ""
            except (NoSuchElementException, StaleElementReferenceException): pass
        elif ai_name == "Gemini":
            try: elems = driver.find_elements(*Selectors.GEMINI_RESPONSE); current_text_on_page = elems[-1].text if elems else ""
            except (NoSuchElementException, StaleElementReferenceException): pass
        elif ai_name == "ChatGPT":
            try: turns = driver.find_elements(*Selectors.CHATGPT_TURN); current_text_on_page = turns[-1].find_element(*Selectors.CHATGPT_RESPONSE_TEXT).text if turns else ""
            except (NoSuchElementException, StaleElementReferenceException): pass

        if ai_name == "Gemini" and current_text_on_page:
            all_brackets = PRIVATE_COMMAND_FIND_REGEX.findall(current_text_on_page)
            new_commands = {b for b in all_brackets if PRIVATE_COMMAND_PARSE_REGEX.match(b) and b not in processed_private_commands["Gemini"]}
            if new_commands:
                log.info(f"[Streaming] (Active) {len(new_commands)} naye valid private commands detect.")
                handle_private_commands(driver, list(new_commands), state) # Pass state
                processed_private_commands["Gemini"].update(new_commands)
        is_generating, is_complete_flag = False, False
        if ai_name == "Deepseek":
            try: is_generating = driver.find_element(*Selectors.DEEPSEEK_STOP).is_displayed()
            except NoSuchElementException: is_generating = False
        elif ai_name == "ChatGPT":
            try: turns = driver.find_elements(*Selectors.CHATGPT_TURN); is_complete_flag = turns and turns[-1].find_element(*Selectors.CHATGPT_COPY_BUTTON).is_displayed()
            except (NoSuchElementException, StaleElementReferenceException): pass
        elif ai_name == "Gemini":
             try: is_generating = driver.find_element(*Selectors.GEMINI_STOP).is_displayed()
             except NoSuchElementException: is_generating = False
        if is_generating:
            if ai_name in potential_dict: potential_dict[ai_name] = None; time.sleep(1); continue
        if not is_generating:
            if ai_name == "ChatGPT" and not is_complete_flag: time.sleep(1); continue
            potential = potential_dict.get(ai_name)
            if potential is not None and current_text_on_page == potential:
                public_text = current_text_on_page; full_text = current_text_on_page
                if ai_name == "Gemini": public_text = PRIVATE_COMMAND_FIND_REGEX.sub('', current_text_on_page).strip()
                if public_text and public_text != state.last_copied_messages_public.get(f"{ai_name}_public", ""):
                    log.info(f"Naya {ai_name} PUBLIC response copy kar raha hai..."); final_text = f"{ai_name}: {public_text}"
                    if ClipboardManager.safe_copy(final_text):
                        last_copied_dict[ai_name] = full_text; state.last_copied_messages_public[f"{ai_name}_public"] = public_text; log.info("Copy successful."); copied = True
                        state.last_processed_clipboard = final_text # Update state clipboard tracker
                    else: log.error("Clipboard copy fail.")
                elif public_text == state.last_copied_messages_public.get(f"{ai_name}_public", ""): copied = True; last_copied_dict[ai_name] = full_text
                elif not public_text and ai_name == "Gemini": log.info("Gemini se sirf command mila."); copied = True; last_copied_dict[ai_name] = full_text
                if ai_name in potential_dict: potential_dict[ai_name] = None; return copied
            elif current_text_on_page != potential: potential_dict[ai_name] = current_text_on_page; time.sleep(1); continue
            elif not current_text_on_page:
                if potential is not None and current_text_on_page == potential: copied = True; return copied
                else: potential_dict[ai_name] = current_text_on_page; time.sleep(1); continue
    if not copied: log.error(f"Timeout ({timeout_seconds}s) for {ai_name}."); return False

@retry_operation
def handle_aistudio_workflow(driver, message_private, state):
    log.info("AI Studio workflow shuru..."); start_time_workflow = time.time(); send_method_used = None
    potential_dict = state.potential_messages
    try:
        send_method_used = send_message(driver, "AIStudio", message_private)
        if not send_method_used: return "[ Private response from AIStudio: Error - Prompt bhej nahi paya. ]"
        log.info(f"Generation ka intezaar (method: {send_method_used}, timeout: 300s)...")
        wait_timeout = 300
        try:
            if send_method_used == 'click':
                start_msg = "Project Chat: Start state 20s mein nahi dikha."; stop_msg = f"Project Chat: Running state {wait_timeout}s mein gayab nahi hua."
                WebDriverWait(driver, 20).until(EC.presence_of_element_located(Selectors.AISTUDIO_PROJECT_SEND_BUTTON_WORKING), message=start_msg); log.info("Generation shuru (Project Send button running)...")
                WebDriverWait(driver, wait_timeout).until_not(EC.presence_of_element_located(Selectors.AISTUDIO_PROJECT_SEND_BUTTON_WORKING), message=stop_msg); log.info("Generation poora (Project Send button idle).")
            elif send_method_used == 'ctrl_enter':
                start_msg = "Homepage: Run button 20s mein disable nahi hua."; stop_msg = f"Homepage: Run button {wait_timeout}s mein enable nahi hua."
                WebDriverWait(driver, 20).until(EC.presence_of_element_located(Selectors.AISTUDIO_HOMEPAGE_RUN_BUTTON_WORKING_SELECTOR), message=start_msg); log.info("Generation shuru (Run button disabled)...")
                WebDriverWait(driver, wait_timeout).until_not(EC.presence_of_element_located(Selectors.AISTUDIO_HOMEPAGE_RUN_BUTTON_WORKING_SELECTOR), message=stop_msg); log.info("Generation poora (Run button enabled).")
            else: raise Exception(f"Unknown send method '{send_method_used}'.")
        except TimeoutException as e:
            log.error(f"Generation wait Timeout: {e.msg}")
            idle_check = Selectors.AISTUDIO_PROJECT_SEND_BUTTON_IDLE if send_method_used == 'click' else Selectors.AISTUDIO_HOMEPAGE_RUN_BUTTON_IDLE
            try: driver.find_element(*idle_check); log.info("Idle state dikh raha hai, maan rahe hain jaldi poora hua.")
            except NoSuchElementException: return f"[ Private response from AIStudio: Error - Generation timeout. Details: {e.msg} ]"
        except Exception as e: log.error(f"Generation wait fail: {e}"); traceback.print_exc(); return f"[ Private response from AIStudio: Error - Generation wait fail: {e} ]"
        time.sleep(2)
        log.info("App save...");
        try:
            save_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable(Selectors.AISTUDIO_SAVE_ENABLED), message="Save 15s mein enable nahi hua."); save_button.click(); log.info("Save click.")
            WebDriverWait(driver, 20).until(EC.presence_of_element_located(Selectors.AISTUDIO_SAVE_DISABLED), message="Save 20s mein disable nahi hua."); log.info("App save ho gaya.")
        except TimeoutException as e: log.info(f"Save timeout. ({e.msg})")
        except Exception as e: log.warning(f"Save fail: {e}. Commit jaari.");
        log.info("GitHub panel..."); github_panel_closed = False
        try:
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable(Selectors.AISTUDIO_GITHUB_BUTTON), message="GitHub button 10s mein nahi mila.").click(); log.info("GitHub button click."); time.sleep(2)
            repo_created = False; commit_processed = False
            try:
                repo_name_box = WebDriverWait(driver, 5).until(EC.presence_of_element_located(Selectors.AISTUDIO_CREATE_REPO_NAME_INPUT), message="'Create Repo' 5s mein nahi mila."); log.info("'Create Repo' form detect."); repo_created = True
                repo_name = f"AiStudio-App-{time.strftime('%Y%m%d-%H%M%S')}"; repo_desc = "AI Studio App by Gemini Admin"
                repo_name_box.send_keys(Keys.CONTROL, 'a'); repo_name_box.send_keys(Keys.DELETE); repo_name_box.send_keys(repo_name); log.info(f"Repo naam: {repo_name}")
                repo_desc_box = driver.find_element(*Selectors.AISTUDIO_CREATE_REPO_DESC_INPUT); repo_desc_box.send_keys(Keys.CONTROL, 'a'); repo_desc_box.send_keys(Keys.DELETE); repo_desc_box.send_keys(repo_desc); log.info("Repo description enter.")
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable(Selectors.AISTUDIO_CREATE_REPO_BUTTON), message="'Create Git repo' 10s mein nahi mila.").click(); log.info("'Create Git repo' click.")
                WebDriverWait(driver, 60).until(EC.presence_of_element_located(Selectors.AISTUDIO_COMMIT_MSG_INPUT), message="Commit box 60s mein nahi aaya after create."); log.info("Repo create successful.")
            except TimeoutException as e:
                if not repo_created: log.info(f"'Create Repo' nahi mila, maan rahe hain 'Commit'. ({e.msg})")
                else:
                    log.warning(f"Repo create ke baad commit screen nahi aaya! ({e.msg}). Checking 'No changes'...");
                    try: WebDriverWait(driver, 5).until(EC.presence_of_element_located(Selectors.AISTUDIO_COMMIT_SUCCESS_MSG)); log.info("'No changes' screen dikha."); commit_processed = True
                    except TimeoutException: log.error("Na commit screen, na 'No changes'!"); raise Exception(f"Post-create state unclear! ({e.msg})")
            if not commit_processed:
                try:
                    commit_msg_box = WebDriverWait(driver, 10).until(EC.presence_of_element_located(Selectors.AISTUDIO_COMMIT_MSG_INPUT), message="Commit box 10s mein nahi mila."); log.debug("Commit box detect.")
                    commit_msg = f"Auto-commit by Gemini Admin @ {time.strftime('%Y-%m-%d %H:%M:%S')}"; commit_msg_box.send_keys(Keys.CONTROL, 'a'); commit_msg_box.send_keys(Keys.DELETE); commit_msg_box.send_keys(commit_msg); log.info("Commit message type.")
                    WebDriverWait(driver, 10).until(EC.element_to_be_clickable(Selectors.AISTUDIO_COMMIT_BUTTON), message="Commit button 10s mein nahi mila.").click(); log.info("Commit button click. 4s wait..."); time.sleep(4)
                    WebDriverWait(driver, 60).until(EC.presence_of_element_located(Selectors.AISTUDIO_COMMIT_SUCCESS_MSG), message="'No changes' 60s mein nahi aaya."); log.info("GitHub action successful!")
                except TimeoutException as commit_timeout:
                     if repo_created: log.warning(f"Post-create commit timeout. ({commit_timeout.msg})");
                     try: WebDriverWait(driver, 5).until(EC.presence_of_element_located(Selectors.AISTUDIO_COMMIT_SUCCESS_MSG)); log.info("'No changes' screen dikha.")
                     except TimeoutException: raise Exception(f"Post-create commit timeout AND 'No changes' screen nahi mila. ({commit_timeout.msg})")
                     else: raise Exception(f"Commit timeout. ({commit_timeout.msg})")
                except Exception as commit_err: raise commit_err
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable(Selectors.AISTUDIO_CLOSE_PANEL), message="Close button 10s mein nahi mila.").click(); github_panel_closed = True; log.info("GitHub panel band.")
        except Exception as e:
            log.error(f"GitHub action fail: {e}"); traceback.print_exc()
            if not github_panel_closed:
                try: log.debug("Closing panel after fail..."); WebDriverWait(driver, 5).until(EC.element_to_be_clickable(Selectors.AISTUDIO_CLOSE_PANEL)).click(); log.info("Panel closed after fail.")
                except: log.warning("Panel close bhi fail.")
            return f"[ Private response from AIStudio: Error - GitHub action fail: {e} ]"
        end_time_workflow = time.time(); log.info(f"Workflow poora hua in {end_time_workflow - start_time_workflow:.2f}s.")
        return "[ Private response from AIStudio: Task poora hua. Code generate, save, aur GitHub par publish/update ho gaya hai. ]"
    except WebDriverException as e: log.error(f"WebDriverException in workflow: {e}"); raise e
    except Exception as e: log.error(f"Unexpected error in workflow: {e}"); traceback.print_exc(); return f"[ Private response from AIStudio: Error - Workflow fail: {e} ]"

def handle_private_commands(driver, commands, state):
    log.info(f"Handling {len(commands)} private commands...")
    for command_string in commands:
        match = PRIVATE_COMMAND_PARSE_REGEX.search(command_string)
        if not match:
            if command_string.startswith("[ Private response from"): log.debug(f"Ignoring processed feedback: {command_string[:50]}...")
            else: log.warning(f"Invalid format, ignoring: {command_string[:50]}...")
            continue
        target_ai, message = match.group(1).strip(), match.group(2).strip(); log.info(f"P-Loop Command -> {target_ai}")
        response_from_ai = f"[ Private response from {target_ai}: Internal Error - No response generated. ]"
        try:
            if target_ai == "AIStudio":
                if switch_to_ai_tab(driver, "AIStudio", state.tab_handles): response_from_ai = handle_aistudio_workflow(driver, message, state)
                else: response_from_ai = "[ Private response from AIStudio: Error - Tab nahi mila. ]"
            elif target_ai in ["Deepseek", "ChatGPT"]:
                if switch_to_ai_tab(driver, target_ai, state.tab_handles):
                    if send_message(driver, target_ai, message):
                        if target_ai in state.potential_messages: state.potential_messages[target_ai] = None
                        private_response = wait_for_private_response(driver, target_ai, state)
                        if private_response is not None: response_from_ai = f"[ Private response from {target_ai}: {private_response} ]"
                        else: response_from_ai = f"[ Private response from {target_ai}: Error - Response timeout. ]"
                    else: response_from_ai = f"[ Private response from {target_ai}: Error - Message bhej nahi paya. ]"
                else: response_from_ai = f"[ Private response from {target_ai}: Error - Tab nahi mila. ]"
            else: log.warning(f"Unknown AI target: {target_ai}"); continue
            log.info(f"P-Loop Response {target_ai} se mila, Admin (Gemini) ko bhej raha hai...")
            if switch_to_ai_tab(driver, "Gemini", state.tab_handles):
                state.processed_private_commands["Gemini"].add(response_from_ai)
                if not send_message(driver, "Gemini", response_from_ai): log.error("Admin ko response bhej nahi paya.")
            else: log.error("Admin tab nahi mila.")
        except WebDriverException as e: log.error(f"WebDriverException in p-loop: {e}"); raise e
        except Exception as e:
             log.error(f"Unexpected error in p-loop: {e}"); traceback.print_exc()
             response_from_ai = f"[ Private response from {target_ai}: Error - Processing failed: {e} ]"
             if switch_to_ai_tab(driver, "Gemini", state.tab_handles): state.processed_private_commands["Gemini"].add(response_from_ai); send_message(driver, "Gemini", response_from_ai)
    log.info("Private Command Loop Samapt.")

def passively_monitor_admin(driver, state):
    ai_name = "Gemini"
    try:
        current_text_on_page = ""
        try:
            response_elements = driver.find_elements(*Selectors.GEMINI_RESPONSE)
            if response_elements: current_text_on_page = response_elements[-1].text
        except (NoSuchElementException, StaleElementReferenceException): return
        if not current_text_on_page: return

        all_brackets = PRIVATE_COMMAND_FIND_REGEX.findall(current_text_on_page)
        new_commands = {b for b in all_brackets if PRIVATE_COMMAND_PARSE_REGEX.match(b) and b not in state.processed_private_commands["Gemini"]}
        if new_commands:
            log.info(f"[Streaming] {len(new_commands)} naye valid private commands detect.")
            handle_private_commands(driver, list(new_commands), state)
            state.processed_private_commands["Gemini"].update(new_commands)
        is_generating = False
        try:
            if driver.find_element(*Selectors.GEMINI_STOP).is_displayed(): is_generating = True
        except NoSuchElementException: is_generating = False
        if is_generating:
            if ai_name in state.potential_messages: state.potential_messages[ai_name] = None; return

        if current_text_on_page == state.last_copied_messages.get(ai_name, ""): return
        potential = state.potential_messages.get(ai_name)
        if potential is not None and current_text_on_page == potential:
            log.info(f"Naya {ai_name} response stable.")
            public_text = PRIVATE_COMMAND_FIND_REGEX.sub('', current_text_on_page).strip()
            full_text = current_text_on_page
            state.last_copied_messages[ai_name] = full_text; state.potential_messages[ai_name] = None
            if public_text and public_text != state.last_copied_messages_public.get(f"{ai_name}_public", ""):
                 log.info(f"Public response {ai_name} se copy kar raha hai...")
                 final_text = f"{ai_name}: {public_text}"
                 if ClipboardManager.safe_copy(final_text):
                     state.last_copied_messages_public[f"{ai_name}_public"] = public_text
                     state.last_processed_clipboard = final_text
                     log.info("Copy successful.")
                 else: log.error("Clipboard copy fail.")
        elif current_text_on_page != potential: state.potential_messages[ai_name] = current_text_on_page

    except (StaleElementReferenceException, NoSuchWindowException): pass
    except WebDriverException as e: raise e
    except Exception as e: log.error(f"Error in passive_check: {e}"); traceback.print_exc(); pass


# --- 5. MAIN SCRIPT LOGIC ---

def main():
    log.info("--- AI Orchestrator Script ---")
    profile_path = os.path.expanduser(USER_DATA_DIR)
    state = AppState()
    state.driver = initialize_driver(profile_path)

    if not state.driver:
        log.critical("Initial driver creation fail. Exiting.")
        return

    monitor_clipboard = input(f"[{ts()}] Kya aap AI-to-AI group chat ke liye clipboard monitoring shuru karna chahte hain? (y/n): ")
    if monitor_clipboard.lower() == 'n':
        log.info("Script band kar di jayegi.")
        if state.driver: state.driver.quit()
        return

    log.info("Clipboard monitoring chalu hai.")
    log.info(f"Browser tabs ko load hone de raha hoon... ({STARTUP_DELAY} seconds)")
    time.sleep(STARTUP_DELAY)
    initialize_tab_management(state.driver, state.tab_handles)
    state.last_processed_clipboard = ClipboardManager.safe_paste()
    loop_counter = 0

    try:
        log.info("Main loop shuru...")
        while True:
            loop_counter += 1
            try:
                # Active Command Check
                current_clipboard = ClipboardManager.safe_paste()
                if current_clipboard != state.last_processed_clipboard:
                    log.debug(f"Clipboard changed! '{current_clipboard[:30]}...'")
                    match = CLIPBOARD_REGEX.search(current_clipboard)
                    if match:
                        target_ai, message_to_send = match.group(1), match.group(2).strip()
                        log.info(f"Active command detect for {target_ai}.")
                        if switch_to_ai_tab(state.driver, target_ai, state.tab_handles):
                            send_method = send_message(state.driver, target_ai, message_to_send)
                            if send_method:
                                state.last_processed_clipboard = current_clipboard
                                wait_for_response(state.driver, target_ai, state)
                        time.sleep(1); continue
                    else:
                        state.last_processed_clipboard = current_clipboard
                
                # Passive Admin Monitoring
                if switch_to_ai_tab(state.driver, "Gemini", state.tab_handles):
                    passively_monitor_admin(state.driver, state)
                time.sleep(LOOP_DELAY)

            except WebDriverException as wd_error:
                log.critical(f"WebDriverException in main loop: {wd_error}")
                traceback.print_exc()
                if state.driver:
                    try: state.driver.quit()
                    except Exception: pass
                log.info(f"Restarting driver in {RESTART_DELAY} seconds...")
                time.sleep(RESTART_DELAY)
                state.driver = initialize_driver(profile_path)
                if not state.driver: break
                initialize_tab_management(state.driver, state.tab_handles)
                state.reset()
                continue
            except Exception as loop_error:
                 log.error(f"Loop error (Iteration {loop_counter}): {loop_error}")
                 traceback.print_exc()
                 log.info("Pausing for 10s..."); time.sleep(10)

    except KeyboardInterrupt:
        log.info("Script ko band kiya ja raha hai (Ctrl+C)...")
    finally:
        if state.driver:
            try: log.info("Final cleanup..."); state.driver.quit()
            except Exception: pass
        log.info("Goodbye!")

if __name__ == "__main__":
    main()