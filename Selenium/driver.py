import os
import urllib.request
import json
import zipfile
import stat

print("🔍 Google API se latest verified Chrome versions fetch kar rahe hain...")
api_url = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"

try:
    # 1. Fetching verified URLs dynamically
    with urllib.request.urlopen(api_url) as response:
        data = json.loads(response.read())
        
    # Stable channel ka data nikalna
    stable_data = data["channels"]["Stable"]
    version = stable_data["version"]
    
    # linux64 ka extract karna
    chromedriver_downloads = stable_data["downloads"]["chromedriver"]
    download_url = next(item["url"] for item in chromedriver_downloads if item["platform"] == "linux64")
    
    print(f"✅ Found Stable Version: {version}")
    print(f"🔗 Verified URL: {download_url}")
    
    # 2. Setup paths
    target_dir = f"/home/mohit/.cache/selenium/chromedriver/linux64/{version}"
    target_path = os.path.join(target_dir, "chromedriver")
    zip_path = "/tmp/chromedriver_dynamic.zip"
    
    # 3. Downloading
    print(f"📥 Downloading ChromeDriver {version}...")
    os.makedirs(target_dir, exist_ok=True)
    urllib.request.urlretrieve(download_url, zip_path)
    
    # 4. Extracting & Permissions
    print("🛠️ Extract karke executable permissions set kar rahe hain...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extract("chromedriver-linux64/chromedriver", "/tmp/")
        
    os.rename("/tmp/chromedriver-linux64/chromedriver", target_path)
    # +x (executable) permission de rahe hain
    os.chmod(target_path, os.stat(target_path).st_mode | stat.S_IEXEC)
    
    # 5. Cleanup
    os.remove(zip_path)
    os.rmdir("/tmp/chromedriver-linux64")
    
    print(f"\n🚀 Boom! ChromeDriver successfully install ho gaya yahan:\n{target_path}")
    print(f"\n⚠️ ZAROORI KAAM: Apni roo_compatible.py me driver_executable_path ko update karna mat bhoolna!")
    print(f'Jaise: driver_executable_path="{target_path}"')

except Exception as e:
    print(f"❌ Error aa gaya: {e}")
