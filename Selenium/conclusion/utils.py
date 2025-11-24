import time
import pyperclip
import logging
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException, WebDriverException
from functools import wraps
from datetime import datetime

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] - %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger(__name__)

# --- Timestamp Function ---
def ts():
    return datetime.now().strftime("%H:%M:%S")

# --- Retry Decorator ---
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

# --- Clipboard Manager ---
class ClipboardManager:
    @staticmethod
    def safe_copy(text, max_attempts=3):
        for attempt in range(max_attempts):
            try:
                pyperclip.copy(text)
                time.sleep(0.3)
                if pyperclip.paste().strip() == text.strip():
                    log.debug(f"Clipboard copy verified for text: '{text[:30]}...'")
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

# --- Driver Health Monitor ---
def is_driver_healthy(driver):
    if not driver:
        return False
    try:
        _ = driver.current_url
        return True
    except WebDriverException:
        log.warning("Driver health check failed: Session is lost.")
        return False