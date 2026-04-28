# Save this as login.py and run it in your terminal: python login.py
from telethon import TelegramClient

API_ID = 21399734
API_HASH = "d4ab4c044abbe71eeb40feb0fd644eb5"

print("Logging into Telegram User Account...")
client = TelegramClient('user', API_ID, API_HASH)
client.start()
print("✅ Successfully logged in! A 'user.session' file has been created.")
print("You can now safely run your MCP server.")