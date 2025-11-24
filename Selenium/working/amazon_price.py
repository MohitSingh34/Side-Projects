import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

# -- The URL you provided --
PRODUCT_URL = "https://www.amazon.in/Apple-iPhone-15-128-GB/dp/B0CHX1W1XY"
# ----------------------------------------------------------------

print("Browser shuru kar raha hoon...")
options = webdriver.ChromeOptions()
# Let's add another option to prevent the "Chrome is being controlled" banner
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

driver = webdriver.Chrome(options=options)

try:
    print(f"Product page par ja raha hoon...")
    driver.minimize_window()
    driver.get(PRODUCT_URL)
    time.sleep(3)

    # --- THIS IS THE UPDATED LOGIC ---
    # We will now look for the element with the class 'a-offscreen'
    # This usually contains the full, clean price.
    price_element = driver.find_element(By.CSS_SELECTOR, ".a-offscreen")
    
    price = price_element.text

    print("\n--- PRODUCT PRICE ---")
    if price:
        print(f"Price Found: {price}")
    else:
        # If .text fails, we try getting the content directly from the HTML
        price = price_element.get_attribute("innerHTML")
        print(f"Price Found (using innerHTML): {price}")

    print("-----------------------\n")

except NoSuchElementException:
    print("\n--- ERROR ---")
    print("Price element (.a-offscreen) nahi mila! Amazon ka layout badal gaya hai, ya CAPTCHA dikha raha hai.")
    print("Browser mein check karo ki page kaisa dikh raha hai.")
    print("-------------\n")
except Exception as e:
    print(f"Ek anjaan error aa gaya: {e}")

finally:
    print("10 second mein browser band ho jaayega...")
    time.sleep(10)
    driver.quit()
    print("Script khatam!")  
    
