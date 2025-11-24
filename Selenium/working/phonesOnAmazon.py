import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SEARCH_TERM = "smartphone"

print("Browser shuru kar raha hoon...")
options = webdriver.ChromeOptions()
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

driver = webdriver.Chrome(options=options)
driver.maximize_window()

try:
    driver.get("https://www.amazon.in/")
    search_bar = driver.find_element(By.ID, "twotabsearchtextbox")
    search_bar.send_keys(SEARCH_TERM)
    print(f"'{SEARCH_TERM}' type kiya...")
    search_bar.send_keys(Keys.RETURN)
    print("Enter press karke search kiya.")

    print("Search results page load hone ka intezaar kar raha hoon...")
    wait = WebDriverWait(driver, 10)
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div[data-asin]")))
    print("Results page loaded!")

    product_results = driver.find_elements(By.CSS_SELECTOR, "div[data-asin]:not(.s-widget-spacing-large)")
    
    print(f"\n--- TOP {min(10, len(product_results))} PHONE PRICES ---\n")

    count = 0
    for product in product_results:
        if count >= 10:
            break
        
        product_name = ""
        product_price = ""

        try:
            # --- THIS IS THE ONLY LINE THAT CHANGED ---
            # We are now looking for an h2 tag for the name, not a span tag.
            product_name = product.find_element(By.CSS_SELECTOR, "h2.a-text-normal").text
            product_price = product.find_element(By.CSS_SELECTOR, "span.a-price-whole").text
        except NoSuchElementException:
            continue
        
        if product_name and product_price:
            print(f"Name: {product_name}")
            print(f"Price: ₹{product_price}")
            print("-" * 20)
            count += 1

except TimeoutException:
    print("Page load timeout! Products nahi mile.")
except Exception as e:
    print(f"Ek anjaan error aa gaya: {e}")
finally:
    print("\nScript khatam! Browser 5 second mein band ho jaayega.")
    time.sleep(5)
    driver.quit()