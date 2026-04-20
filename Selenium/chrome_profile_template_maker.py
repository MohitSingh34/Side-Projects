import os
import shutil

# --- Configuration Paths ---
SOURCE_PROFILE = "/home/mohit/chrome-profile-v4"
TEMPLATE_DIR = "/home/mohit/chrome-worker-master-template"
ZIP_FILE_PATH = "/home/mohit/chrome-worker-master-template" # shutil.make_archive adds the .zip extension automatically

def create_master_template():
    print(f"🔍 Checking source profile: {SOURCE_PROFILE}")
    if not os.path.exists(SOURCE_PROFILE):
        print(f"❌ Error: Source profile '{SOURCE_PROFILE}' does not exist.")
        return

    # 1. Clean up old template if it exists so we get a fresh snapshot
    if os.path.exists(TEMPLATE_DIR):
        print(f"🗑️ Removing old template directory: {TEMPLATE_DIR}")
        shutil.rmtree(TEMPLATE_DIR)

    # 2. Clone the profile while ignoring locks and heavy caches
    print("🚀 Cloning active profile into clean template (skipping caches & locks)...")
    try:
        shutil.copytree(
            SOURCE_PROFILE,
            TEMPLATE_DIR,
            ignore=shutil.ignore_patterns(
                'SingletonLock', 'SingletonCookie', 'SingletonSocket',
                'Cache*', 'GPUCache', 'Code Cache', 'Network Persistent State'
            )
        )
        print(f"✅ Successfully created clean template folder at: {TEMPLATE_DIR}")
    except Exception as e:
        print(f"❌ Failed to copy profile: {e}")
        return

    # 3. Create a zip backup of the clean template
    print("📦 Zipping the template folder for backup...")
    try:
        # shutil.make_archive(base_name, format, root_dir)
        shutil.make_archive(ZIP_FILE_PATH, 'zip', TEMPLATE_DIR)
        print(f"✅ Successfully created zip backup at: {ZIP_FILE_PATH}.zip")
    except Exception as e:
        print(f"❌ Failed to zip template: {e}")
        return

    print("\n🎉 All done! You now have a clean template folder AND a zip backup.")

if __name__ == "__main__":
    create_master_template()
