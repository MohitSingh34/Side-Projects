import time
from selenium import webdriver # type: ignore
from selenium.webdriver.common.by import By # type: ignore
# --- NEW IMPORT! This is for handling dropdowns ---
from selenium.webdriver.support.ui import Select # pyright: ignore[reportMissingImports]

print("Browser shuru kar raha hoon...")
driver = webdriver.Chrome()

try:
    # 1. Form page par jao
    driver.get("https://formy-project.herokuapp.com/form")
    print("Form page loaded.")
    time.sleep(1)

    # 2. Basic text fields bharo
    driver.find_element(By.ID, "first-name").send_keys("Mohit")
    driver.find_element(By.ID, "last-name").send_keys("Sharma")
    driver.find_element(By.ID, "job-title").send_keys("Automation Engineer")
    print("Text fields bhar diye.")
    time.sleep(1)

    # 3. Radio button select karo
    # Radio buttons ko bas click karna hota hai
    driver.find_element(By.ID, "radio-button-2").click()
    print("Radio button select kar liya.")
    time.sleep(1)

    # 4. Checkbox select karo
    driver.find_element(By.ID, "checkbox-1").click()
    print("Checkbox select kar liya.")
    time.sleep(1)

    # 5. Dropdown menu se option select karo
    # YEH HAI NAYI CHEEZ!
    experience_dropdown = driver.find_element(By.ID, "select-menu")
    select = Select(experience_dropdown)
    
    # Aap inmein se koi bhi tareeka use kar sakte ho:
    # select.select_by_index(2)         # '2-4' select karega
    select.select_by_visible_text("5-9") # '5-9' select karega
    # select.select_by_value("4")       # '10+' select karega
    print("Dropdown se option '5-9' select kar liya.")
    time.sleep(1)

    # 6. Date select karo
    driver.find_element(By.ID, "datepicker").send_keys("10/20/2025") # Date type kar di
    print("Date daal di.")
    time.sleep(1)

    # 7. Submit button par click karo
    driver.find_element(By.CSS_SELECTOR, ".btn.btn-primary").click()
    print("Form submit kar diya!")

    # 8. Success page load hone ka wait karo
    time.sleep(3)
    success_message = driver.find_element(By.CLASS_NAME, "alert-success").text
    print("\n--- RESULT ---")
    print(f"Success Message: {success_message}")
    print("--------------\n")

except Exception as e:
    print(f"Ek anjaan error aa gaya: {e}")

finally:
    print("Browser 5 second mein band ho jaayega.")
    time.sleep(5)
    driver.quit()