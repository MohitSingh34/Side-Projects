# Seleniumfix : Please learn and fix me


import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException

def setup_driver():
    """Sets up the Chrome driver to use a specific user profile."""
    options = webdriver.ChromeOptions()
    
    # === FIX APPLIED HERE ===
    # Humne ek NAYI profile directory ka path diya hai.
    # Ab yeh aapke main Chrome browser ke saath conflict nahi karega.
    # Yeh directory apne aap ban jaayegi agar मौजूद nahi hai.
    options.add_argument("user-data-dir=/home/mohit/.config/google-chrome/")
    
    # WebDriverManager automatically downloads and sets up the correct driver.
    service = Service(ChromeDriverManager().install())
    
    driver = webdriver.Chrome(service=service, options=options)
    driver.maximize_window()
    return driver

def switch_to_latest_tab(driver):
    """Waits for a new tab and switches to the most recently opened one."""
    # Wait until there is more than one tab.
    wait = WebDriverWait(driver, 10)
    # Check if more than one window handle exists before waiting.
    if len(driver.window_handles) > 1:
        wait.until(EC.new_window_is_opened(driver.window_handles))
    
    # Switch to the last window handle (the newest tab).
    latest_window = driver.window_handles[-1]
    driver.switch_to.window(latest_window)
    print(f"Switched to new tab: {driver.title}")

def find_movie(driver, movie_name):
    """Follows the recorded steps to get the download link for Episode 1."""
    wait = WebDriverWait(driver, 20)

    # 1. Website par jaao
    print("Opening hdhub4u...")
    # The domain might change, so let's try a more reliable one or the one from your log
    driver.get("https://hdhub4u.cologne/")

    # 2. Movie/Series search karo
    print(f"Searching for '{movie_name}'...")
    search_box = wait.until(EC.visibility_of_element_located((By.ID, "s")))
    search_box.send_keys(movie_name)
    search_box.submit()

    # 3. Search result par click karo
    print("Finding the movie link in search results...")
    movie_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "article.post-item a")))
    print(f"Found series: {movie_link.text}. Clicking it...")
    movie_link.click()

    # 4. Episode 1 ke download link par click karo
    print("Looking for Episode 1 download link...")
    episode_link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "E01")))
    print("Found link for Episode 1. Clicking it...")
    episode_link.click()

    # 5. Ad/Verification pages ko handle karo
    original_window = driver.current_window_handle
    
    print("Handling verification page 1...")
    switch_to_latest_tab(driver)
    
    try:
        verify_button = wait.until(EC.element_to_be_clickable((By.ID, "verify_btn")))
        print("Found 'Verify' button, clicking it...")
        verify_button.click()
        time.sleep(1)
        verify_button.click()
    except TimeoutException:
        print("Could not find the 'verify_btn'. The website flow might have changed.")
        return

    print("Handling verification page 2...")
    hubcloud_link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "HubCloud Server")))
    print("Found HubCloud link. Clicking it...")
    hubcloud_link.click()
    
    # 6. Final download page par switch karo
    print("Switching to the final download page...")
    switch_to_latest_tab(driver)
    
    # 7. Final download button dhoondho
    final_download_button = wait.until(EC.element_to_be_clickable((By.ID, "download")))
    download_link = final_download_button.get_attribute('href')
    
    print("\n" + "="*50)
    print("🎉 Mission Accomplished! Final Download Link Found! 🎉")
    print(f"Link: {download_link}")
    print("="*50 + "\n")
    
    time.sleep(20)


if __name__ == "__main__":
    movie_to_find = "marvels iron fist" 
    driver = None
    try:
        driver = setup_driver()
        find_movie(driver, movie_to_find)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("The script failed. This could be due to a change in the website's structure or a network issue.")
    finally:
        if driver:
            driver.quit()
            print("Browser closed.")

