import time
from selenium import webdriver
from selenium.webdriver.common.by import By
# --- NEW IMPORT! This is for complex actions ---
from selenium.webdriver.common.action_chains import ActionChains

print("Browser shuru kar raha hoon...")
driver = webdriver.Chrome()
driver.maximize_window()

try:
    # 1. Page par jao
    driver.get("https://the-internet.herokuapp.com/drag_and_drop")
    print("Drag and Drop page loaded.")
    time.sleep(2)

    # 2. Source aur Target elements ko dhoondo
    source_element = driver.find_element(By.ID, "column-a")
    target_element = driver.find_element(By.ID, "column-b")

    print("Elements dhoond liye. Ab drag and drop karunga...")

    # 3. ActionChains ka istemal karke drag and drop perform karo
    # YEH HAI NAYI CHEEZ!
    actions = ActionChains(driver) # ActionChains object banaya
    
    # Drag and drop action ko chain mein add kiya
    actions.drag_and_drop(source_element, target_element)
    
    # Saare actions ko perform karo
    actions.perform()
    
    print("Drag and Drop complete!")
    time.sleep(3)

    # 4. Verify karo ki swap hua ya nahi
    # Hum 'column-a' wale box ka header text check karte hain. Shuru mein 'A' tha.
    header_after_drop = driver.find_element(By.ID, "column-a").find_element(By.TAG_NAME, "header").text

    print("\n--- RESULT ---")
    if header_after_drop == 'B':
        print("SUCCESS! Boxes have been swapped.")
    else:
        print("FAIL! Boxes did not swap.")
    print("--------------\n")

except Exception as e:
    print(f"Ek anjaan error aa gaya: {e}")

finally:
    print("Browser 5 second mein band ho jaayega.")
    time.sleep(5)
    driver.quit()