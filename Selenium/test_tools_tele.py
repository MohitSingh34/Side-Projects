import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
# Safe target for normal messages (Saved Messages)
TEST_CHAT = "me"

# IMPORTANT: To test Admin Tools (Ban, Title, Mute, etc.), 
# create a dummy group where you are the owner, and paste its ID here.
# Example: TEST_GROUP = -100987654321
TEST_GROUP = -1003998465520 
# ==========================================

async def main():
    print("📦 Generating dummy files for media tests...")
    dummy_doc = os.path.abspath("test_doc.txt")
    dummy_photo = os.path.abspath("test_photo.jpg") 
    dummy_video = os.path.abspath("test_video.mp4")
    dummy_audio = os.path.abspath("test_audio.mp3")
    
    with open(dummy_doc, "w") as f: f.write("Hello World")
    # Using tiny, valid headers for media so Telegram doesn't reject them as "fake"
    with open(dummy_photo, "wb") as f: f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t")
    with open(dummy_video, "wb") as f: f.write(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom")
    with open(dummy_audio, "wb") as f: f.write(b"ID3\x03\x00\x00\x00\x00\x00\x00")

    server_params = StdioServerParameters(command="python", args=["telegram_mcp.py"])
    
    admin_target = TEST_GROUP if TEST_GROUP else TEST_CHAT

    tests = [
        # --- Phase 1: Base & Discovery ---
        {"name": "get_dialog_list", "args": {"limit": 20}},
        # --- Phase 2: Core Messaging ---
        {"name": "send_telegram_message", "args": {"chat_id": "Mudit", "message": "🤖 V3 Test Run Initiated"}},   {"name": "send_safe_bot_to_bot_message", "args": {"bot_username": "@BotFather", "message": "/cancel"}},
      
        # --- Phase 5: Fetch for Manipulation ---
           ]

    with open("v3_logs.txt", "w", encoding="utf-8") as log_file:
        def log(msg):
            print(msg)
            log_file.write(msg + "\n")

        log("🚀 Starting V3 Telegram MCP Test...\n" + "="*50)
        if TEST_GROUP:
            log(f"📌 Admin tests routing to Group ID: {TEST_GROUP}")
        else:
            log("⚠️ No TEST_GROUP provided. Admin tests will target 'me' and fail safely.")
        log("="*50 + "\n")

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    log("✅ Connected to telegram_mcp.py\n")

                    for test in tests:
                        tool_name = test["name"]
                        args = test["args"]
                        log(f"▶️ Testing: {tool_name}")
                        
                        try:
                            result = await session.call_tool(tool_name, arguments=args)
                            
                            if result.isError:
                                log(f"   ⚠️ Expected/Handled Error: {result.content[0].text}\n")
                            else:
                                log(f"   ✅ Success: {result.content[0].text}\n")
                                
                                # Dynamic Message Manipulation Injection
                                if tool_name == "read_telegram_messages":
                                    try:
                                        text_out = result.content[0].text
                                        last_msg_id = int(text_out.split("(ID: ")[1].split(")")[0])
                                        log(f"   [Grabbed Message ID {last_msg_id} for manipulation tests]")
                                        
                                        manipulation_tests = [
                                            {"name": "react_to_telegram_message", "args": {"chat_id": TEST_CHAT, "message_id": last_msg_id, "emoji": "👍"}},
                                            {"name": "pin_telegram_message", "args": {"chat_id": TEST_CHAT, "message_id": last_msg_id}},
                                            {"name": "forward_telegram_message", "args": {"from_chat_id": TEST_CHAT, "to_chat_id": TEST_CHAT, "message_id": last_msg_id}},
                                            {"name": "edit_telegram_message", "args": {"chat_id": TEST_CHAT, "message_id": last_msg_id, "new_text": "✏️ V3 Edit Success"}},
                                            {"name": "download_telegram_media", "args": {"chat_id": TEST_CHAT, "message_id": last_msg_id, "save_path": os.path.abspath("downloaded_test")}},
                                            {"name": "mark_message_as_read", "args": {"chat_id": TEST_CHAT, "message_id": last_msg_id}},
                                            {"name": "delete_telegram_message", "args": {"chat_id": TEST_CHAT, "message_id": last_msg_id}},
                                        ]
                                        for i, m_test in enumerate(manipulation_tests):
                                            tests.insert(tests.index(test) + 1 + i, m_test)
                                            
                                    except Exception as e:
                                        log(f"   ⚠️ Couldn't extract ID for manipulation: {e}")

                        except Exception as e:
                            log(f"   ❌ CRITICAL CRASH: {str(e)}\n")
                        
                        await asyncio.sleep(2.5) # Anti-spam delay

        except Exception as e:
            log(f"\n❌ Failed to boot server: {str(e)}")

    print("\n🧹 Cleaning up dummy files...")
    for f in [dummy_doc, dummy_photo, dummy_video, dummy_audio]:
        if os.path.exists(f): os.remove(f)

    print("✅ Testing Complete! Check v3_logs.txt")

if __name__ == "__main__":
    asyncio.run(main())