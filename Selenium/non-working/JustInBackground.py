# [] : Not working
# future : Not working

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

PRODUCT_URL = "https://www.amazon.in/Apple-iPhone-15-128-GB/dp/B0CHX1W1XY"

# --- Headless options taiyaar karo ---
headless_options = webdriver.ChromeOptions()
headless_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
headless_options.add_experimental_option("excludeSwitches", ["enable-automation"])
headless_options.add_argument("--window-size=1920,1080")
headless_options.add_argument("--disable-blink-features=AutomationControlled")
headless_options.add_argument("--headless")

driver = webdriver.Chrome(options=headless_options)

try:
    # --- STEP 1: Headless mode mein koshish karo ---
    print("Browser ko STEALTH HEADLESS mode mein shuru kar raha hoon...")
    
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        'source': "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    print("Product page par ja raha hoon (background mein)...")
    driver.get(PRODUCT_URL)

    print("Page source ko save kar raha hoon...")
    with open("page.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("Page source 'page.html' file mein save ho gaya.")

    print("Price element ke load hone ka intezaar kar raha hoon...")
    wait = WebDriverWait(driver, 10)
    
    # --- SELECTOR UPDATED based on your new HTML ---
    price_element = wait.until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "span.a-price-whole"))
    )
    
    # .text will cleanly get the numbers from the element
    price = price_element.text

    print("\n--- PRODUCT PRICE (from headless browser) ---")
    if price:
        print(f"Price Found: ₹{price}")
    print("------------------------------------------\n")
    
    driver.quit()
    print("Script safalta se poori hui! Headless browser band kar diya.")

except TimeoutException:
    # --- STEP 2: Error ko pakdo aur GUI mode mein switch karo ---
    print("\n--- HUMAN INTERVENTION REQUIRED ---")
    print("Headless mode fail ho gaya. GUI mode shuru kar raha hoon...")
    
    failed_url = driver.current_url
    driver.quit()

    gui_options = webdriver.ChromeOptions()
    gui_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    print("Normal browser window khul raha hai...")
    gui_driver = webdriver.Chrome(options=gui_options)
    gui_driver.get(failed_url)
    gui_driver.maximize_window()
    
    # --- STEP 3: User se help maango ---
    input("Please page ko theek karein (e.g., CAPTCHA solve karein) aur fir yahan Enter dabayein...")
    
    # --- STEP 4: Dobara koshish karo ---
    try:
        print("\nAapke intervention ke baad dobara koshish kar raha hoon...")
        wait = WebDriverWait(gui_driver, 10)
        
        # --- SELECTOR UPDATED based on your new HTML (for the GUI part too) ---
        price_element = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "span.a-price-whole"))
        )
        price = price_element.text

        print("\n--- PRODUCT PRICE (from GUI browser) ---")
        if price:
            print(f"Price Found: ₹{price}")
        print("--------------------------------------\n")
        print("Is baar kaam ho gaya!")

    except Exception as e:
        print(f"\nGUI mode mein bhi element nahi mila. Shayad selector galat hai. Error: {e}")
    
    finally:
        print("Script khatam! GUI browser 10 second mein band ho jaayega.")
        time.sleep(10)
        gui_driver.quit()