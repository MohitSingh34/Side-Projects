# Zaroori libraries import karein
import time
from selenium import webdriver
from selenium.webdriver.common.by import By

# 1. Chrome browser shuru karo
print("Browser shuru kar raha hoon...")
driver = webdriver.Chrome()

# 2. Website par jao
print("Login page par ja raha hoon...")
driver.get("http://quotes.toscrape.com/login")

# Thoda wait karo taaki page aaram se load ho jaaye
time.sleep(2)

# 3. Username field dhoondo aur usmein type karo
# Hum 'ID' se element dhoond rahe hain.
print("Username type kar raha hoon...")
username_field = driver.find_element(By.ID, "username")
print("Username field", username_field)
username_field.send_keys("abcde") # Aap koi bhi fake username daal sakte hain

time.sleep(1) # Har step ke baad thoda rukte hain taaki dikhe kya ho raha hai
# 4. Password field dhoondo aur usmein type karo
# Hum 'ID' se element dhoond rahe hain.
print("Password type kar raha hoon...")
password_field = driver.find_element(By.ID, "password")
print("Password field", password_field)
password_field.send_keys("password123") # Koi bhi fake password

time.sleep(1)

# 5. Login button dhoondo aur uspar click karo
# Hum 'CSS Selector' se element dhoond rahe hain.
print("Login button par click kar raha hoon...")
login_button = driver.find_element(By.CSS_SELECTOR, "input.btn")
login_button.click()

# 6. Check karo ki login hua ya nahi
# Login hone ke baad "Logout" link dikhna chahiye
try:
    logout_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Logout")
    print("Login Successful! 'Logout' link mil gaya.")
except:
    print("Login Failed! 'Logout' link nahi mila.")


# 5 second ruko taaki hum result dekh sakein
print("5 second mein browser band ho jaayega...")
time.sleep(5)

# 7. Browser ko band kar do
driver.quit()
print("Script khatam!")