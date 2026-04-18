import asyncio
import requests
import os
import json
import time
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolResult
from collections import defaultdict

app = Server("telegram-super-mcp")

# Anti-loop memory: Tracks target_bot_id -> [timestamps of recent messages]
bot_interaction_history = defaultdict(list)

# Strict configuration: Maximum 3 messages to the same bot within 60 seconds
MAX_BOT_REPLIES = 3
BOT_RATE_LIMIT_WINDOW = 10

# 👇 Yahan apna BotFather wala Token aur apna Chat ID daalo
BOT_TOKEN = "8666398252:AAFnBdxKkpOD_eITcHYRoFIqJw4OQ6mOgNQ"
# Public Group ID for @itsworkspac
CHAT_ID = "-1002364966348"

# Fixed the URL string
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Memory to track read messages so it doesn't read old ones again
last_update_id = 0

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        # --- MEDIA & MESSAGING TOOLS ---
        Tool(
            name="send_telegram_message",
            description="Sends a text message directly to Telegram.",
            inputSchema={"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}
        ),
        Tool(
            name="send_telegram_photo",
            description="Sends an image/screenshot to Telegram. Provide the absolute local file path.",
            inputSchema={"type": "object", "properties": {"photo_path": {"type": "string"}, "caption": {"type": "string"}}, "required": ["photo_path"]}
        ),
        # --- ADVANCED & BUSINESS TOOLS ---
        Tool(
            name="set_bot_menu_button",
            description="Configures the main menu button for the bot (e.g., to open a Web App or show commands).",
            inputSchema={
                "type": "object",
                "properties": {
                    "menu_text": {"type": "string", "description": "Text to show on the button"},
                    "web_app_url": {"type": "string", "description": "Optional: URL if it's a web app"}
                },
                "required": ["menu_text"]
            }
        ),
        Tool(
            name="send_business_message",
            description="Sends a message on behalf of a user via Telegram Business Mode.",
            inputSchema={
                "type": "object",
                "properties": {
                    "business_connection_id": {"type": "string"},
                    "chat_id": {"type": "string"},
                    "text": {"type": "string"}
                },
                "required": ["business_connection_id", "chat_id", "text"]
            }
        ),
        Tool(
            name="manage_chat_join_request",
            description="Approves or declines a user's request to join a group or channel where the bot is admin.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer"},
                    "action": {"type": "string", "enum": ["approve", "decline"]}
                },
                "required": ["user_id", "action"]
            }
        ),
        Tool(
            name="send_safe_bot_to_bot_message",
            description="Safely sends or replies to a message to another bot with strict infinite-loop prevention.",
            inputSchema={
                "type": "object",
                "properties": {
                    "target_bot_id": {"type": "string"},
                    "text": {"type": "string"}
                },
                "required": ["target_bot_id", "text"]
            }
        ),
        Tool(
            name="send_telegram_document",
            description="Sends a file, log, or document to Telegram. Provide the absolute local file path.",
            inputSchema={"type": "object", "properties": {"document_path": {"type": "string"}, "caption": {"type": "string"}}, "required": ["document_path"]}
        ),
        Tool(
            name="send_telegram_video",
            description="Sends a video file to Telegram. Provide the absolute local file path.",
            inputSchema={"type": "object", "properties": {"video_path": {"type": "string"}, "caption": {"type": "string"}}, "required": ["video_path"]}
        ),
        Tool(
            name="send_telegram_poll",
            description="Sends a poll to the Telegram chat. Options must be an array of strings (2-10 options).",
            inputSchema={"type": "object", "properties": {"question": {"type": "string"}, "options": {"type": "array", "items": {"type": "string"}}}, "required": ["question", "options"]}
        ),
        Tool(
            name="read_telegram_messages",
            description="Reads the latest unread messages sent by the user in the Telegram chat.",
            inputSchema={"type": "object", "properties": {}}
        ),
        # --- MESSAGE MANAGEMENT TOOLS ---
        Tool(
            name="edit_telegram_message",
            description="Edits an already sent text message. Requires the message_id.",
            inputSchema={"type": "object", "properties": {"message_id": {"type": "integer"}, "new_text": {"type": "string"}}, "required": ["message_id", "new_text"]}
        ),
        Tool(
            name="delete_telegram_message",
            description="Deletes a message from the chat. Requires message_id.",
            inputSchema={"type": "object", "properties": {"message_id": {"type": "integer"}}, "required": ["message_id"]}
        ),
        Tool(
            name="pin_telegram_message",
            description="Pins a specific message in the group.",
            inputSchema={"type": "object", "properties": {"message_id": {"type": "integer"}}, "required": ["message_id"]}
        ),
        # --- CHAT & GROUP MANAGEMENT TOOLS ---
        Tool(
            name="get_chat_info",
            description="Gets basic information about the current chat, like member count and title.",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="set_telegram_chat_title",
            description="Changes the title of the Telegram group.",
            inputSchema={"type": "object", "properties": {"new_title": {"type": "string"}}, "required": ["new_title"]}
        ),
        Tool(
            name="ban_telegram_member",
            description="Bans (kicks) a user from the group. Requires their user_id.",
            inputSchema={"type": "object", "properties": {"user_id": {"type": "integer"}}, "required": ["user_id"]}
        ),
        Tool(
            name="unban_telegram_member",
            description="Unbans a previously banned user from the group.",
            inputSchema={"type": "object", "properties": {"user_id": {"type": "integer"}}, "required": ["user_id"]}
        ),
        Tool(
            name="mute_telegram_member",
            description="Restricts a user from sending messages (read-only mode) for a specific duration in minutes.",
            inputSchema={"type": "object", "properties": {"user_id": {"type": "integer"}, "duration_minutes": {"type": "integer"}}, "required": ["user_id", "duration_minutes"]}
        ),
        Tool(
            name="create_telegram_invite_link",
            description="Generates a new invite link for the group.",
            inputSchema={"type": "object", "properties": {}}
        ),
        # --- COMMANDER LEVEL UPGRADES ---
        Tool(
            name="send_telegram_voice",
            description="Sends an OGG audio file as a playable voice note.",
            inputSchema={"type": "object", "properties": {"voice_path": {"type": "string"}, "caption": {"type": "string"}}, "required": ["voice_path"]}
        ),
        Tool(
            name="set_telegram_admin_title",
            description="Sets a custom title for an administrator in the group.",
            inputSchema={"type": "object", "properties": {"user_id": {"type": "integer"}, "custom_title": {"type": "string"}}, "required": ["user_id", "custom_title"]}
        ),
        Tool(
            name="get_telegram_chat_member",
            description="Gets detailed information about a specific member of the chat.",
            inputSchema={"type": "object", "properties": {"user_id": {"type": "integer"}}, "required": ["user_id"]}
        ),
        Tool(
            name="set_telegram_chat_photo",
            description="Changes the group's profile picture. Provide absolute path to the image.",
            inputSchema={"type": "object", "properties": {"photo_path": {"type": "string"}}, "required": ["photo_path"]}
        ),
        # --- FANCY & SECURITY UPGRADES ---
        Tool(
            name="react_to_telegram_message",
            description="Adds an emoji reaction to a specific message. Supported emojis: 👍, 👎, ❤️, 🔥, 🎉, 🤩, 😱, 😁, 😢, 💩, etc.",
            inputSchema={"type": "object", "properties": {"message_id": {"type": "integer"}, "emoji": {"type": "string"}}, "required": ["message_id", "emoji"]}
        ),
        Tool(
            name="send_telegram_location",
            description="Sends precise GPS coordinates to the group.",
            inputSchema={"type": "object", "properties": {"latitude": {"type": "number"}, "longitude": {"type": "number"}}, "required": ["latitude", "longitude"]}
        ),
        Tool(
            name="create_secure_invite_link",
            description="Generates a temporary invite link that expires after specified minutes or limited uses.",
            inputSchema={"type": "object", "properties": {"expire_minutes": {"type": "integer"}, "member_limit": {"type": "integer"}}, "required": ["expire_minutes"]}
        ),
        Tool(
            name="promote_telegram_member",
            description="Promotes a normal member to Admin with specific management rights.",
            inputSchema={"type": "object", "properties": {"user_id": {"type": "integer"}}, "required": ["user_id"]}
        ),
        Tool(
            name="set_telegram_chat_description",
            description="Updates the group's bio/description.",
            inputSchema={"type": "object", "properties": {"description": {"type": "string"}}, "required": ["description"]}
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    global last_update_id
    
    # --- MEDIA & MESSAGING LOGIC ---
    if name == "send_telegram_message":
        msg = arguments.get("message")
        payload = {"chat_id": CHAT_ID, "text": msg}
        try:
            resp = requests.post(f"{BASE_URL}/sendMessage", json=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                msg_id = data.get("result", {}).get("message_id")
                return CallToolResult(content=[TextContent(type="text", text=f"✅ Message sent (ID: {msg_id}): {msg}")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Failed: {resp.text}")], isError=True)
        except Exception as e:
            return CallToolResult(content=[TextContent(type="text", text=f"API Error: {str(e)}")], isError=True)

    elif name == "send_telegram_photo":
        path = arguments.get("photo_path")
        caption = arguments.get("caption", "")
        if not os.path.exists(path):
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Error: Image not found at {path}")], isError=True)
        try:
            with open(path, 'rb') as f:
                resp = requests.post(f"{BASE_URL}/sendPhoto", data={"chat_id": CHAT_ID, "caption": caption}, files={"photo": f})
            if resp.status_code == 200:
                return CallToolResult(content=[TextContent(type="text", text=f"📸 Photo sent successfully from {path}")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Failed: {resp.text}")], isError=True)
        except Exception as e:
            return CallToolResult(content=[TextContent(type="text", text=f"API Error: {str(e)}")], isError=True)

    elif name == "send_telegram_document":
        path = arguments.get("document_path")
        caption = arguments.get("caption", "")
        if not os.path.exists(path):
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Error: File not found at {path}")], isError=True)
        try:
            with open(path, 'rb') as f:
                resp = requests.post(f"{BASE_URL}/sendDocument", data={"chat_id": CHAT_ID, "caption": caption}, files={"document": f})
            if resp.status_code == 200:
                return CallToolResult(content=[TextContent(type="text", text=f"📁 Document sent successfully from {path}")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Failed: {resp.text}")], isError=True)
        except Exception as e:
            return CallToolResult(content=[TextContent(type="text", text=f"API Error: {str(e)}")], isError=True)

    elif name == "send_telegram_video":
        path = arguments.get("video_path")
        caption = arguments.get("caption", "")
        if not os.path.exists(path):
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Error: Video not found at {path}")], isError=True)
        try:
            with open(path, 'rb') as f:
                resp = requests.post(f"{BASE_URL}/sendVideo", data={"chat_id": CHAT_ID, "caption": caption}, files={"video": f})
            if resp.status_code == 200:
                return CallToolResult(content=[TextContent(type="text", text=f"🎥 Video sent successfully from {path}")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Failed: {resp.text}")], isError=True)
        except Exception as e:
            return CallToolResult(content=[TextContent(type="text", text=f"API Error: {str(e)}")], isError=True)

    elif name == "send_telegram_poll":
        question = arguments.get("question")
        options = arguments.get("options")
        if len(options) < 2 or len(options) > 10:
            return CallToolResult(content=[TextContent(type="text", text="❌ A poll must have between 2 and 10 options.")], isError=True)
        try:
            payload = {"chat_id": CHAT_ID, "question": question, "options": json.dumps(options)}
            resp = requests.post(f"{BASE_URL}/sendPoll", data=payload, timeout=10)
            if resp.status_code == 200:
                return CallToolResult(content=[TextContent(type="text", text="📊 Poll sent successfully.")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Failed: {resp.text}")], isError=True)
        except Exception as e:
            return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)

    elif name == "read_telegram_messages":
        try:
            resp = requests.get(f"{BASE_URL}/getUpdates", params={"offset": last_update_id + 1, "timeout": 5})
            if resp.status_code == 200:
                data = resp.json()
                messages = []
                for res in data.get("result", []):
                    last_update_id = res["update_id"]
                    if "message" in res and "text" in res["message"]:
                        sender = res["message"]["from"].get("first_name", "User")
                        msg_id = res["message"]["message_id"]
                        text = res["message"]["text"]
                        messages.append(f"{sender} (ID: {msg_id}): {text}")
                
                if messages:
                    return CallToolResult(content=[TextContent(type="text", text="New Telegram Messages:\n" + "\n".join(messages))])
                else:
                    return CallToolResult(content=[TextContent(type="text", text="No new messages right now.")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Failed to read messages: {resp.text}")], isError=True)
        except Exception as e:
            return CallToolResult(content=[TextContent(type="text", text=f"API Error: {str(e)}")], isError=True)
        
    # --- MESSAGE MANAGEMENT LOGIC ---
    elif name == "edit_telegram_message":
        try:
            payload = {"chat_id": CHAT_ID, "message_id": arguments.get("message_id"), "text": arguments.get("new_text")}
            resp = requests.post(f"{BASE_URL}/editMessageText", json=payload, timeout=5)
            if resp.status_code == 200: return CallToolResult(content=[TextContent(type="text", text="✏️ Message edited successfully.")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Edit Failed: {resp.text}")], isError=True)
        except Exception as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)

    elif name == "delete_telegram_message":
        try:
            payload = {"chat_id": CHAT_ID, "message_id": arguments.get("message_id")}
            resp = requests.post(f"{BASE_URL}/deleteMessage", json=payload, timeout=5)
            if resp.status_code == 200: return CallToolResult(content=[TextContent(type="text", text="🗑️ Message deleted.")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Delete Failed: {resp.text}")], isError=True)
        except Exception as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)

    elif name == "pin_telegram_message":
        try:
            payload = {"chat_id": CHAT_ID, "message_id": arguments.get("message_id")}
            resp = requests.post(f"{BASE_URL}/pinChatMessage", json=payload, timeout=5)
            if resp.status_code == 200: return CallToolResult(content=[TextContent(type="text", text="📌 Message pinned.")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Pin Failed: {resp.text}")], isError=True)
        except Exception as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)

    # --- CHAT & GROUP MANAGEMENT LOGIC ---
    elif name == "get_chat_info":
        try:
            resp_chat = requests.get(f"{BASE_URL}/getChat", params={"chat_id": CHAT_ID})
            resp_count = requests.get(f"{BASE_URL}/getChatMemberCount", params={"chat_id": CHAT_ID})
            
            info = ""
            if resp_chat.status_code == 200:
                chat_data = resp_chat.json().get("result", {})
                info += f"Title: {chat_data.get('title', 'N/A')}\nType: {chat_data.get('type', 'N/A')}\nDescription: {chat_data.get('description', 'N/A')}\n"
            if resp_count.status_code == 200:
                info += f"Member Count: {resp_count.json().get('result', 'Unknown')}"
                
            return CallToolResult(content=[TextContent(type="text", text=f"Chat Info:\n{info}")])
        except Exception as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)

    elif name == "set_telegram_chat_title":
        try:
            payload = {"chat_id": CHAT_ID, "title": arguments.get("new_title")}
            resp = requests.post(f"{BASE_URL}/setChatTitle", json=payload, timeout=5)
            if resp.status_code == 200: return CallToolResult(content=[TextContent(type="text", text="🏷️ Chat title updated successfully.")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Title Update Failed: {resp.text}")], isError=True)
        except Exception as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)

    elif name == "ban_telegram_member":
        try:
            payload = {"chat_id": CHAT_ID, "user_id": arguments.get("user_id")}
            resp = requests.post(f"{BASE_URL}/banChatMember", json=payload, timeout=5)
            if resp.status_code == 200: return CallToolResult(content=[TextContent(type="text", text=f"🔨 User {arguments.get('user_id')} banned.")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Ban Failed: {resp.text}")], isError=True)
        except Exception as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)

    elif name == "unban_telegram_member":
        try:
            payload = {"chat_id": CHAT_ID, "user_id": arguments.get("user_id"), "only_if_banned": True}
            resp = requests.post(f"{BASE_URL}/unbanChatMember", json=payload, timeout=5)
            if resp.status_code == 200: return CallToolResult(content=[TextContent(type="text", text=f"🕊️ User {arguments.get('user_id')} unbanned.")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Unban Failed: {resp.text}")], isError=True)
        except Exception as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)

    elif name == "mute_telegram_member":
        try:
            user_id = arguments.get("user_id")
            minutes = arguments.get("duration_minutes")
            until_date = int(time.time()) + (minutes * 60)
            
            # Setting all permissions to False mutes the user
            permissions = {
                "can_send_messages": False,
                "can_send_audios": False,
                "can_send_documents": False,
                "can_send_photos": False,
                "can_send_videos": False,
                "can_send_video_notes": False,
                "can_send_voice_notes": False,
                "can_send_polls": False,
                "can_send_other_messages": False
            }
            
            payload = {"chat_id": CHAT_ID, "user_id": user_id, "until_date": until_date, "permissions": json.dumps(permissions)}
            resp = requests.post(f"{BASE_URL}/restrictChatMember", data=payload, timeout=5)
            if resp.status_code == 200: 
                return CallToolResult(content=[TextContent(type="text", text=f"🤐 User {user_id} has been muted for {minutes} minutes.")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Mute Failed: {resp.text}")], isError=True)
        except Exception as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)

    elif name == "create_telegram_invite_link":
        try:
            payload = {"chat_id": CHAT_ID}
            resp = requests.post(f"{BASE_URL}/exportChatInviteLink", json=payload, timeout=5)
            if resp.status_code == 200: 
                link = resp.json().get("result")
                return CallToolResult(content=[TextContent(type="text", text=f"🔗 New Invite Link: {link}")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Link generation Failed: {resp.text}")], isError=True)
        except Exception as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)

    # --- COMMANDER LEVEL LOGIC ---
    elif name == "send_telegram_voice":
        try:
            path = arguments.get("voice_path")
            if not os.path.exists(path): return CallToolResult(content=[TextContent(type="text", text="❌ Voice file not found.")], isError=True)
            with open(path, 'rb') as f:
                resp = requests.post(f"{BASE_URL}/sendVoice", data={"chat_id": CHAT_ID, "caption": arguments.get("caption", "")}, files={"voice": f})
            if resp.status_code == 200: return CallToolResult(content=[TextContent(type="text", text="🎙️ Voice note sent successfully!")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Failed: {resp.text}")], isError=True)
        except Exception as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)

    elif name == "set_telegram_admin_title":
        try:
            payload = {"chat_id": CHAT_ID, "user_id": arguments.get("user_id"), "custom_title": arguments.get("custom_title")}
            resp = requests.post(f"{BASE_URL}/setChatAdministratorCustomTitle", json=payload, timeout=5)
            if resp.status_code == 200: return CallToolResult(content=[TextContent(type="text", text=f"🏷️ Custom title set for user {arguments.get('user_id')}")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Failed: {resp.text}")], isError=True)
        except Exception as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)

    elif name == "get_telegram_chat_member":
        try:
            resp = requests.get(f"{BASE_URL}/getChatMember", params={"chat_id": CHAT_ID, "user_id": arguments.get("user_id")}, timeout=5)
            if resp.status_code == 200:
                member_data = resp.json().get("result", {})
                status = member_data.get("status", "unknown")
                user = member_data.get("user", {})
                info = f"User: {user.get('first_name')} (ID: {user.get('id')})\nStatus: {status}\nIs Bot: {user.get('is_bot')}"
                return CallToolResult(content=[TextContent(type="text", text=f"👤 Member Info:\n{info}")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Failed: {resp.text}")], isError=True)
        except Exception as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)

    elif name == "set_telegram_chat_photo":
        try:
            path = arguments.get("photo_path")
            if not os.path.exists(path): return CallToolResult(content=[TextContent(type="text", text="❌ Photo not found.")], isError=True)
            with open(path, 'rb') as f:
                resp = requests.post(f"{BASE_URL}/setChatPhoto", data={"chat_id": CHAT_ID}, files={"photo": f})
            if resp.status_code == 200: return CallToolResult(content=[TextContent(type="text", text="🖼️ Group DP changed successfully!")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Failed: {resp.text}")], isError=True)
        except Exception as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)

    # --- FANCY & SECURITY LOGIC ---
    elif name == "react_to_telegram_message":
        try:
            message_id = arguments.get("message_id")
            emoji = arguments.get("emoji")
            payload = {
                "chat_id": CHAT_ID,
                "message_id": message_id,
                "reaction": [{"type": "emoji", "emoji": emoji}]
            }
            resp = requests.post(f"{BASE_URL}/setMessageReaction", json=payload, timeout=5)
            if resp.status_code == 200:
                return CallToolResult(content=[TextContent(type="text", text=f"{emoji} Reaction added successfully!")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Reaction Failed: {resp.text}")], isError=True)
        except Exception as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)

    elif name == "send_telegram_location":
        try:
            payload = {
                "chat_id": CHAT_ID,
                "latitude": arguments.get("latitude"),
                "longitude": arguments.get("longitude")
            }
            resp = requests.post(f"{BASE_URL}/sendLocation", json=payload, timeout=5)
            if resp.status_code == 200:
                return CallToolResult(content=[TextContent(type="text", text="📍 Location pinned in chat.")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Location Failed: {resp.text}")], isError=True)
        except Exception as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)

    elif name == "create_secure_invite_link":
        try:
            minutes = arguments.get("expire_minutes")
            limit = arguments.get("member_limit", 0)
            expire_date = int(time.time()) + (minutes * 60)
            
            payload = {"chat_id": CHAT_ID, "expire_date": expire_date}
            if limit > 0: payload["member_limit"] = limit
                
            resp = requests.post(f"{BASE_URL}/createChatInviteLink", json=payload, timeout=5)
            if resp.status_code == 200:
                link = resp.json().get("result", {}).get("invite_link")
                return CallToolResult(content=[TextContent(type="text", text=f"🔐 Secure Invite Link (Expires in {minutes} mins): {link}")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Secure Link Failed: {resp.text}")], isError=True)
        except Exception as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)

    elif name == "promote_telegram_member":
        try:
            payload = {
                "chat_id": CHAT_ID,
                "user_id": arguments.get("user_id"),
                "can_manage_chat": True,
                "can_delete_messages": True,
                "can_invite_users": True,
                "can_restrict_members": True,
                "can_pin_messages": True
            }
            resp = requests.post(f"{BASE_URL}/promoteChatMember", json=payload, timeout=5)
            if resp.status_code == 200:
                return CallToolResult(content=[TextContent(type="text", text=f"⭐ User {arguments.get('user_id')} promoted to Admin!")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Promotion Failed: {resp.text}")], isError=True)
        except Exception as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)

    elif name == "set_telegram_chat_description":
        try:
            payload = {"chat_id": CHAT_ID, "description": arguments.get("description")}
            resp = requests.post(f"{BASE_URL}/setChatDescription", json=payload, timeout=5)
            if resp.status_code == 200:
                return CallToolResult(content=[TextContent(type="text", text="📝 Chat description updated.")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Description Update Failed: {resp.text}")], isError=True)
        except Exception as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)

    # --- ADVANCED & BUSINESS LOGIC ---
    elif name == "set_bot_menu_button":
        try:
            menu_text = arguments.get("menu_text")
            web_app_url = arguments.get("web_app_url")
            
            menu_button = {"type": "web_app", "text": menu_text, "web_app": {"url": web_app_url}} if web_app_url else {"type": "commands"}
            
            payload = {"menu_button": json.dumps(menu_button)}
            resp = requests.post(f"{BASE_URL}/setChatMenuButton", json=payload, timeout=5)
            
            if resp.status_code == 200:
                return CallToolResult(content=[TextContent(type="text", text=f"✨ Menu button updated to: {menu_text}")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Menu Update Failed: {resp.text}")], isError=True)
        except Exception as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)

    elif name == "send_business_message":
        try:
            payload = {
                "business_connection_id": arguments.get("business_connection_id"),
                "chat_id": arguments.get("chat_id"),
                "text": arguments.get("text")
            }
            resp = requests.post(f"{BASE_URL}/sendMessage", json=payload, timeout=5)
            if resp.status_code == 200:
                return CallToolResult(content=[TextContent(type="text", text="💼 Business message sent successfully!")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Business Send Failed: {resp.text}")], isError=True)
        except Exception as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)

    elif name == "manage_chat_join_request":
        try:
            action = arguments.get("action")
            payload = {"chat_id": CHAT_ID, "user_id": arguments.get("user_id")}
            
            endpoint = "/approveChatJoinRequest" if action == "approve" else "/declineChatJoinRequest"
            resp = requests.post(f"{BASE_URL}{endpoint}", json=payload, timeout=5)
            
            if resp.status_code == 200:
                return CallToolResult(content=[TextContent(type="text", text=f"✅ Join request {action}d successfully.")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Action Failed: {resp.text}")], isError=True)
        except Exception as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)

    elif name == "send_safe_bot_to_bot_message":
        try:
            target_bot = arguments.get("target_bot_id")
            current_time = time.time()
            
            # --- Loop Prevention Logic (Sliding Window) ---
            bot_interaction_history[target_bot] = [
                ts for ts in bot_interaction_history[target_bot] 
                if current_time - ts < BOT_RATE_LIMIT_WINDOW
            ]
            
            if len(bot_interaction_history[target_bot]) >= MAX_BOT_REPLIES:
                warning_msg = f"⚠️ Loop Prevention Triggered: Ignored message to bot {target_bot}. Exceeded {MAX_BOT_REPLIES} msgs/min."
                print(warning_msg)
                return CallToolResult(content=[TextContent(type="text", text=warning_msg)], isError=True)
            
            bot_interaction_history[target_bot].append(current_time)
            # ----------------------------------------------

            payload = {
                "chat_id": CHAT_ID, 
                "text": arguments.get("text")
            }
            resp = requests.post(f"{BASE_URL}/sendMessage", json=payload, timeout=5)
            
            if resp.status_code == 200:
                return CallToolResult(content=[TextContent(type="text", text=f"🤖 Safe bot-to-bot message sent! (Count: {len(bot_interaction_history[target_bot])}/{MAX_BOT_REPLIES})")])
            return CallToolResult(content=[TextContent(type="text", text=f"❌ Send Failed: {resp.text}")], isError=True)
        except Exception as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)
                
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())