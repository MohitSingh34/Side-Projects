import time
from selenium import webdriver
from selenium.webdriver.common.by import By

print("Browser shuru kar raha hoon...")
driver = webdriver.Chrome()

try:
    # 1. Page par jao
    driver.get("https://the-internet.herokuapp.com/windows")
    print("Page loaded.")

    # 2. Original tab ka ID save kar lo, taaki hum wapas aa sakein
    original_window = driver.current_window_handle
    print(f"Original tab ka ID: {original_window}")

    # 3. Link dhoondo aur click karo jo naya tab kholega
    driver.find_element(By.LINK_TEXT, "Click Here").click()
    print("Link click kiya, naya tab khulna chahiye.")
    time.sleep(2) # Naye tab ko khulne ka time do

    # 4. Saare open tabs ke IDs ki list nikalo
    # YEH HAI NAYI CHEEZ!
    all_windows = driver.window_handles
    print(f"Ab total {len(all_windows)} tabs khule hain.")

    # 5. Naye tab par switch karo
    for window_handle in all_windows:
        if window_handle != original_window:
            driver.switch_to.window(window_handle)
            # Jaise hi naya tab mil jaaye, loop se bahar aa jao
            break
    
    # 6. Naye tab par kaam karo (e.g., text print karo)
    new_tab_text = driver.find_element(By.TAG_NAME, "h3").text
    print(f"Naye tab par switch kiya. Yahan likha hai: '{new_tab_text}'")
    time.sleep(2)

    # 7. Naye tab ko band kar do
    # driver.close() sirf current tab ko band karta hai
    driver.close()
    print("Naya tab band kar diya.")
    time.sleep(1)

    # 8. Original tab par wapas switch karo
    driver.switch_to.window(original_window)
    print("Original tab par wapas aa gaya.")

    # 9. Original tab par kuch kaam karke prove karo ki hum wapas aa gaye
    original_tab_text = driver.find_element(By.TAG_NAME, "h3").text
    print(f"Original tab par likha hai: '{original_tab_text}'")

except Exception as e:
    print(f"Ek anjaan error aa gaya: {e}")

finally:
    print("\nBrowser 5 second mein band ho jaayega.")
    time.sleep(5)
    # driver.quit() saare tabs/windows ko band karta hai
    driver.quit()