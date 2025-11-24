import time
from selenium import webdriver
from selenium.webdriver.common.by import By

# -- Aap yahan search topic badal sakte hain --
SEARCH_TOPIC = "Python programming language"
# -------------------------------------------

print("Browser shuru kar raha hoon...")
driver = webdriver.Chrome()

try:
    driver.get("https://www.wikipedia.org/")
    print("Wikipedia khul gaya.")
    time.sleep(1)

    search_bar = driver.find_element(By.ID, "searchInput")
    print(f"'{SEARCH_TOPIC}' ke liye search kar raha hoon...")
    search_bar.send_keys(SEARCH_TOPIC)
    time.sleep(1)

    search_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    search_button.click()
    print("Search button click kiya.")
    time.sleep(2)

    # 5. YEH PART BADAL GAYA HAI: Result page se SAARe paragraphs dhoondo
    print("Saare paragraphs nikal raha hoon...")
    # Note: 'find_elements' (plural) ka istemal
    all_paragraphs = driver.find_elements(By.CSS_SELECTOR, "#mw-content-text .mw-parser-output p")

    # 6. Pehla non-empty paragraph dhoondo
    first_meaningful_paragraph = ""
    for paragraph in all_paragraphs:
        # .strip() extra space hata deta hai. Agar text hai, toh hi aage badho.
        if paragraph.text.strip():
            first_meaningful_paragraph = paragraph.text
            break  # Jaise hi pehla paragraph mil jaaye, loop rok do

    # 7. Result print karo
    print("\n--- RESULT ---")
    if first_meaningful_paragraph:
        print(first_meaningful_paragraph)
    else:
        print("Koi bhi paragraph nahi mila jisme text ho.")
    print("--------------\n")

except Exception as e:
    print(f"Ek error aa gaya: {e}")

finally:
    print("5 second mein browser band ho jaayega...")
    time.sleep(5)
    driver.quit()
    print("Script khatam!")