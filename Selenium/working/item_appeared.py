import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

# --- NEW IMPORTS for smart waiting ---
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

print("Browser shuru kar raha hoon...")
driver = webdriver.Chrome()

try:
    # 1. Page par jao
    driver.get("https://the-internet.herokuapp.com/dynamic_loading/2")
    print("Page loaded.")

    # 2. "Start" button dhoondo aur click karo
    start_button = driver.find_element(By.CSS_SELECTOR, "#start button")
    start_button.click()
    print("Start button click kiya. Content ab load ho raha hai...")

    # 3. Smart Wait: 10 second tak intezaar karo jab tak "finish" element DIKH na jaaye
    # YEH HAI NAYI AUR SABSE IMPORTANT CHEEZ!
    wait = WebDriverWait(driver, 10) # 10 second ka max timeout set kiya
    
    # Hum wait ko bata rahe hain ki 'finish' ID wale element ke 'visible' hone tak ruke
    finish_element = wait.until(EC.visibility_of_element_located((By.ID, "finish")))
    
    print("Content load ho gaya! 'Hello World!' ab visible hai.")

    # 4. Element se text nikalo aur print karo
    message = finish_element.text
    print("\n--- RESULT ---")
    print(f"Loaded Message: {message}")
    print("--------------\n")

except TimeoutException:
    print("\n--- ERROR ---")
    print("Wait timeout ho gaya! Element 10 second mein load nahi hua.")
    print("--------------\n")
except Exception as e:
    print(f"Ek anjaan error aa gaya: {e}")

finally:
    print("Browser 5 second mein band ho jaayega.")
    time.sleep(5)
    driver.quit()


    