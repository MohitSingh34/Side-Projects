from selenium.webdriver.common.by import By

# --- General Settings ---
USER_DATA_DIR = "~/chrome-profile-uc" 
WINDOW_WIDTH = 273
WINDOW_HEIGHT = 768
STARTUP_DELAY = 10 
LOOP_DELAY = 2 
RESTART_DELAY = 15 

# --- Regex Patterns ---
PRIVATE_COMMAND_FIND_REGEX_PATTERN = r"(\[.*?\])"
PRIVATE_COMMAND_PARSE_REGEX_PATTERN = r"^\s*\[\s*type\s*:\s*private message\s*;\s*for\s*:\s*(Deepseek|ChatGPT|AIStudio)\s*;\s*message\s*:\s*{(.*?)}\s*\]\s*$"
CLIPBOARD_REGEX_PATTERN = r"\[ Conversation till (Deepseek|ChatGPT|Gemini)'s last message : (.*) \]"

# --- AI URLs for Tab Management ---
AI_URLS = {
    "ChatGPT": ["chatgpt.com", "chat.openai.com"],
    "Deepseek": ["deepseek.com"],
    "Gemini": ["gemini.google.com"],
    "AIStudio": ["aistudio.google.com/apps/drive/", "aistudio.google.com/apps"]
}


# --- SELECTORS ---
class Selectors:
    # --- Gemini (Admin) ---
    GEMINI_STOP = (By.CSS_SELECTOR, 'button.send-button.stop[aria-label="Stop response"]')
    GEMINI_RESPONSE = (By.CSS_SELECTOR, 'message-content .markdown')
    GEMINI_INPUT = (By.CSS_SELECTOR, 'div[role="textbox"][aria-label="Enter a prompt here"]')
    GEMINI_SEND = (By.CSS_SELECTOR, 'button[aria-label="Send message"]')

    # --- Deepseek ---
    DEEPSEEK_STOP = (By.CSS_SELECTOR, "button[data-testid='stop-button']")
    DEEPSEEK_INPUT = (By.CSS_SELECTOR, "textarea[placeholder*='Message DeepSeek']")
    DEEPSEEK_RESPONSE_CONTAINER = (By.CSS_SELECTOR, "div[class*='_4f9bf79']")
    DEEPSEEK_RESPONSE_TEXT = (By.XPATH, ".//div[contains(@class, 'ds-markdown')]")

    # --- ChatGPT ---
    CHATGPT_TURN = (By.CSS_SELECTOR, 'article[data-turn="assistant"]')
    CHATGPT_COPY_BUTTON = (By.CSS_SELECTOR, "button[data-testid='copy-turn-action-button']")
    CHATGPT_RESPONSE_TEXT = (By.CSS_SELECTOR, ".markdown")
    CHATGPT_INPUT = (By.ID, "prompt-textarea")
    CHATGPT_SEND = (By.CSS_SELECTOR, "button[data-testid='send-button']")

    # --- AI Studio ---
    # Scenario 1: Inside a project (Code assistant)
    AISTUDIO_PROJECT_INPUT = (By.CSS_SELECTOR, 'textarea[placeholder="Make changes, add new features, ask for anything"]')
    AISTUDIO_PROJECT_SEND_BUTTON_WORKING = (By.CSS_SELECTOR, 'button[aria-label="Send"].running')
    AISTUDIO_PROJECT_SEND_BUTTON_IDLE = (By.CSS_SELECTOR, 'button[aria-label="Send"]:not(.running)')

    # Scenario 2: Homepage (App Generator)
    AISTUDIO_HOMEPAGE_INPUT = (By.CSS_SELECTOR, 'textarea[aria-label="Enter a prompt to generate an app"]')
    AISTUDIO_HOMEPAGE_RUN_BUTTON_WORKING = (By.CSS_SELECTOR, 'ms-run-button button[aria-label="Run"][disabled]')
    AISTUDIO_HOMEPAGE_RUN_BUTTON_IDLE = (By.CSS_SELECTOR, 'ms-run-button button[aria-label="Run"]:not([disabled])')

    # Common AI Studio Selectors (Save & Commit)
    AISTUDIO_SAVE_ENABLED = (By.CSS_SELECTOR, 'button[aria-label="Save app"]:not([aria-disabled="true"])')
    AISTUDIO_SAVE_DISABLED = (By.CSS_SELECTOR, 'button[aria-label="Save app"][aria-disabled="true"]')
    AISTUDIO_GITHUB_BUTTON = (By.CSS_SELECTOR, 'ms-github-trigger-button button[aria-label="Save to GitHub"]')
    AISTUDIO_CLOSE_PANEL = (By.CSS_SELECTOR, 'button[aria-label="Close panel"]')

    # GitHub Panel Selectors
    AISTUDIO_COMMIT_MSG_INPUT = (By.CSS_SELECTOR, 'textarea[formcontrolname="message"]')
    AISTUDIO_COMMIT_BUTTON = (By.CSS_SELECTOR, 'button[aria-label="Push latest changes to GitHub"]')
    AISTUDIO_CREATE_REPO_NAME_INPUT = (By.CSS_SELECTOR, 'input[formcontrolname="name"]')
    AISTUDIO_CREATE_REPO_DESC_INPUT = (By.CSS_SELECTOR, 'input[formcontrolname="description"]')
    AISTUDIO_CREATE_REPO_BUTTON = (By.CSS_SELECTOR, 'button[aria-label="Create github repository"]')
    AISTUDIO_COMMIT_SUCCESS_MSG = (By.XPATH, "//div[contains(@class, 'central-content')]//span[contains(text(), 'No changes to commit')]")