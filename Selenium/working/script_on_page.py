import time
from selenium import webdriver
from selenium.webdriver.common.by import By

print("Browser shuru kar raha hoon...")
driver = webdriver.Chrome()
driver.implicitly_wait(5) # Thoda sa implicit wait daal dete hain
# [] : kjkk
try:
    driver.get("https://the-internet.herokuapp.com/infinite_scroll")
    print("Infinite scroll page loaded.")
    time.sleep(2)

    last_count = 0
    match_count = 0
    
    # Hum 5 baar scroll karne ki koshish karenge
    for i in range(5):
        # Current paragraph count check karo
        current_paragraphs = driver.find_elements(By.CLASS_NAME, "jscroll-added")
        current_count = len(current_paragraphs)
        print(f"Abhi total paragraphs hain: {current_count}")

        # Agar pichli baar se count nahi badha, toh shayad hum end tak pahunch gaye hain
        if current_count == last_count:
            match_count += 1
            if match_count >= 2: # Agar 2 baar se count nahi badha, toh break
                print("Lagta hai page ke end tak pahunch gaye hain.")
                break
        else:
            match_count = 0 # Agar count badha toh reset counter

        last_count = current_count

        # --- YEH HAI NAYA LOGIC ---
        # Ab hum window nahi, balki specific div ko scroll kar rahe hain
        print(f"Scroll attempt #{i+1}...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Naye content ko load hone ka time do
        time.sleep(1.5)

    print("\nScrolling poori ho gayi!")
    
    final_paragraphs = driver.find_elements(By.CLASS_NAME, "jscroll-added")

    print("\n--- RESULT ---")
    print(f"Shuru mein 0 paragraphs the (dynamically loaded).")
    print(f"Scroll karne ke baad total paragraphs hain: {len(final_paragraphs)}")
    if len(final_paragraphs) > 0:
        print("SUCCESS! Naya content load ho gaya hai.")
    else:
        print("FAIL! Naya content load nahi hua.")
    print("--------------\n")

except Exception as e:
    print(f"Ek anjaan error aa gaya: {e}")

finally:
    print("Browser 5 second mein band ho jaayega.")
    time.sleep(5)
    driver.quit()