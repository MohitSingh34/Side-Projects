import threading
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
import time
import os

# Har browser thread yeh function chalayega
def run_automation(url, task_name):
    # Har thread ko apna log message milega
    print(f"[Thread: {task_name}] 🚀 Shuru ho raha hai...")
    
    # Har thread ko apna 'driver' object banana ZAROORI hai
    options = webdriver.FirefoxOptions()
    options.headless = True # Screen par 5 browser pop-up nahi honge
    
    # 'devnull' par log discard karke console saaf rakhte hain
    service = Service(GeckoDriverManager().install(), log_path=os.devnull) 
    driver = None # Pehle se define kar rahe hain taaki 'finally' mein use ho sake
    
    try:
        # 1. Naya browser session shuru karo
        driver = webdriver.Firefox(service=service, options=options)
        
        # 2. Automation task
        driver.get(url)
        # Title print karke proof denge ki page load hua
        print(f"[Thread: {task_name}] ✅ URL '{url}' load ho gaya. Title: {driver.title[:30]}...") # Title ko chhota kar rahe hain
        
        # Thoda sa rukte hain simulation ke liye
        time.sleep(3) 
        
    except Exception as e:
        print(f"[Thread: {task_name}] ❌ ERROR: {e}")
        
    finally:
        # 3. Task poora hone par driver ko band karna
        if driver:
            driver.quit()
        print(f"[Thread: {task_name}] 🏁 Poora ho gaya, browser band.")

# --- Main script yahan se shuru hota hai ---

# 1. Humare 5 tasks
tasks = [
    {"name": "Google", "url": "https://www.google.com"},
    {"name": "Wikipedia", "url": "https://www.wikipedia.org"},
    {"name": "GitHub", "url": "https://www.github.com"},
    {"name": "DuckDuckGo", "url": "https://www.duckduckgo.com"},
    {"name": "Example", "url": "https://www.example.com"}
]

threads = [] # Threads ko store karne ke liye

print("--- Main Script: 5 Parallel Automations Launch Kar Raha Hoon ---")

# 2. Har task ke liye ek naya thread banao aur shuru karo
for task in tasks:
    t = threading.Thread(target=run_automation, args=(task["url"], task["name"]))
    threads.append(t)
    t.start() # Thread ko "Run" state mein bhejta hai

# 3. Sabhi threads ke poora hone ka intezaar karo
# 'join()' ka matlab hai "Main script aage nahi badhega jab tak yeh thread poora na ho"
for t in threads:
    t.join()

print("--- Main Script: Sabhi 5 Parallel Tasks Poore Ho Gaye Hain! ---")