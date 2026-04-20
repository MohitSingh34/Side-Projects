#!/usr/bin/env python3
"""
Telegram MCP Server using Telethon (MTProto) - USER ACCOUNT MODE
Provides full Telegram client capabilities. Can interact with ANY user, group, channel, or bot.
"""

import asyncio
import os
import sys
import time
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolResult
from telethon import TelegramClient
from telethon import types
import json  # Add this if not already present
from telethon import events  # Add this line
from telethon.tl.functions.messages import GetAvailableReactionsRequest

CACHE_FILE = "/tmp/telegram_free_reactions.json"
# API Credentials
API_ID = 21399734
API_HASH = "d4ab4c044abbe71eeb40feb0fd644eb5"

app = Server("telegram-telethon-userbot-mcp")

client = None
# Background event collector
new_message_queue = asyncio.Queue()
background_listener_started = False

async def start_background_listener(tc):
    global background_listener_started
    if background_listener_started:
        return
    background_listener_started = True

    @tc.on(events.NewMessage)
    async def handler(event):
        # Store new message info in a queue for later retrieval
        await new_message_queue.put({
            "chat_id": event.chat_id,
            "sender": event.message.sender_id,
            "text": event.message.text or "[media]",
            "date": event.message.date.isoformat(),
            "message_id": event.message.id
        })

async def get_new_messages_since_last_call():
    """Return all messages collected in the queue and clear it."""
    messages = []
    while not new_message_queue.empty():
        try:
            messages.append(new_message_queue.get_nowait())
        except asyncio.QueueEmpty:
            break
    return messages

def format_new_messages(messages):
    """Format queued messages for appending to tool response."""
    if not messages:
        return ""
    lines = ["\n\n📨 **New messages while you were working:**"]
    for m in messages:
        lines.append(f"[Chat {m['chat_id']}] {m['sender']}: {m['text']}")
    return "\n".join(lines)


async def get_free_reactions(client):
    # Check cache
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)

    # Fetch from Telegram
    result = await client(GetAvailableReactionsRequest(hash=0))

    free_emojis = []

    for r in result.reactions:
        # Check if it's premium (handles different Telethon versions)
        is_premium = getattr(r, "premium", getattr(r, "premium_required", False))
        
        if not is_premium:
            if hasattr(r, "reaction"):
                # Sometimes it's a string, sometimes it's a ReactionEmoji object
                if isinstance(r.reaction, str):
                    free_emojis.append(r.reaction)
                elif hasattr(r.reaction, "emoticon"):
                    free_emojis.append(r.reaction.emoticon)

    # Save to cache
    with open(CACHE_FILE, "w") as f:
        json.dump(free_emojis, f)

    return free_emojis
    
async def get_client():
    global client

    if client is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        session_file_path = os.path.join(script_dir, 'user')

        client = TelegramClient(session_file_path, API_ID, API_HASH)

    if not client.is_connected():
        await client.connect()

    if not await client.is_user_authorized():
        raise RuntimeError("User not authorized")
    if not background_listener_started:
        await start_background_listener(client)

    return client

async def get_new_messages_since_last_call():
    """Return all messages collected in the queue and clear it."""
    messages = []
    while not new_message_queue.empty():
        try:
            messages.append(new_message_queue.get_nowait())
        except asyncio.QueueEmpty:
            break
    return messages
async def get_entity_safely(tc, chat_id):
    """Helper to resolve IDs, usernames, phone numbers, or plain display names."""
    if isinstance(chat_id, str):
        # 1. Check if it's a numeric ID stored as a string (e.g., "-100123456")
        if chat_id.lstrip('-').isdigit():
            return await tc.get_entity(int(chat_id))
        
        # 2. Try resolving it as an exact @username or +PhoneNumber
        try:
            return await tc.get_entity(chat_id)
        except ValueError:
            # 3. NEW: If it's a plain name (e.g., "Rahul" or "Mom"),
            # search through the user's active chats/dialogs to find a match.
            async for dialog in tc.iter_dialogs(limit=100): # Searches top 100 recent chats
                if dialog.name and chat_id.lower() in dialog.name.lower():
                    return dialog.entity
            
            # If still not found, throw a clear error
            raise ValueError(f"Could not find any user or group matching the name: '{chat_id}'.")
            
    # Fallback for when chat_id is already an integer
    return await tc.get_entity(chat_id)

@app.list_tools()
@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_dialog_list",
            description="CRITICAL TOOL: Gets a list of recent chats, groups, and bots along with their exact numeric 'chat_id's. If you need to interact with a user/group but don't know their chat_id, ALWAYS call this tool first to find it.",
            inputSchema={"type": "object", "properties": {"limit": {"type": "integer", "default": 20, "description": "The maximum number of recent chats to retrieve."}}}
        ),
        Tool(
            name="read_telegram_messages",
            description="Reads recent messages from a chat. Returns the text, sender info, and the 'message_id' (which is REQUIRED for downloading media, forwarding, or deleting). Call this to read bot responses or find a message_id.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The ID, username, or phone number of the chat to read from."}, "limit": {"type": "integer", "default": 10, "description": "Number of messages to fetch."}}, "required": ["chat_id"]}
        ),
        Tool(
            name="send_telegram_message",
            description="Sends a text message. Dont use plain name ever. Target 'chat_id' can be a numeric ID, an @username, a phone number, or even just a plain display name (e.g., 'Rahul' or 'Family Group').",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target ID, username, phone number, or plain name."}, "message": {"type": "string", "description": "The text content of the message."}}, "required": ["chat_id", "message"]}
        ),
        Tool(
            name="download_telegram_media",
            description="Downloads media (files, videos, photos) from a specific message. You MUST provide the exact 'message_id', which you can find by calling 'read_telegram_messages' first.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "message_id": {"type": "integer", "description": "The exact numeric ID of the message containing the media."}, "save_path": {"type": "string", "description": "Absolute local file path to save the download."}}, "required": ["chat_id", "message_id"]}
        ),
        Tool(
            name="send_telegram_photo",
            description="Sends an image/screenshot. Provide the absolute local file path.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "photo_path": {"type": "string", "description": "Absolute local file path to the image."}, "caption": {"type": "string", "description": "Optional text to send with the image."}}, "required": ["chat_id", "photo_path"]}
        ),
        Tool(
            name="send_telegram_document",
            description="Sends a file, log, or document. Provide the absolute local file path.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "document_path": {"type": "string", "description": "Absolute local file path to the document."}, "caption": {"type": "string", "description": "Optional caption."}}, "required": ["chat_id", "document_path"]}
        ),
        Tool(
            name="send_telegram_video",
            description="Sends a video file.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "video_path": {"type": "string", "description": "Absolute local file path to the video."}, "caption": {"type": "string", "description": "Optional caption."}}, "required": ["chat_id", "video_path"]}
        ),
        Tool(
            name="send_telegram_audio",
            description="Sends an audio file.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "audio_path": {"type": "string", "description": "Absolute local file path to the audio file."}, "caption": {"type": "string", "description": "Optional caption."}}, "required": ["chat_id", "audio_path"]}
        ),
        Tool(
            name="send_telegram_voice",
            description="Sends a voice note.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "voice_path": {"type": "string", "description": "Absolute local file path to the audio file, will be sent as a voice note."}, "caption": {"type": "string", "description": "Optional caption."}}, "required": ["chat_id", "voice_path"]}
        ),
        Tool(
            name="send_telegram_animation",
            description="Sends a GIF animation.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "animation_path": {"type": "string", "description": "Absolute local file path to the GIF or silent video."}, "caption": {"type": "string", "description": "Optional caption."}}, "required": ["chat_id", "animation_path"]}
        ),
        Tool(
            name="send_telegram_media_group",
            description="Sends multiple photos/videos as an album. Provide an array of absolute file paths.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "media_paths": {"type": "array", "items": {"type": "string"}, "description": "Array of absolute local file paths to group into an album."}, "caption": {"type": "string", "description": "Optional caption."}}, "required": ["chat_id", "media_paths"]}
        ),
        Tool(
            name="send_telegram_poll",
            description="Sends a poll to the chat.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "question": {"type": "string", "description": "The poll's main question."}, "options": {"type": "array", "items": {"type": "string"}, "description": "Array of string choices for the poll."}}, "required": ["chat_id", "question", "options"]}
        ),
        Tool(
            name="send_telegram_location",
            description="Sends GPS coordinates.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "latitude": {"type": "number", "description": "Latitude coordinate."}, "longitude": {"type": "number", "description": "Longitude coordinate."}}, "required": ["chat_id", "latitude", "longitude"]}
        ),
        Tool(
            name="edit_telegram_message",
            description="Edits an already sent text message. Requires the message_id.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "message_id": {"type": "integer", "description": "ID of the message you want to edit."}, "new_text": {"type": "string", "description": "The replacement text."}}, "required": ["chat_id", "message_id", "new_text"]}
        ),
        Tool(
            name="delete_telegram_message",
            description="Deletes a message from the chat. Requires the message_id.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "message_id": {"type": "integer", "description": "ID of the message to delete."}}, "required": ["chat_id", "message_id"]}
        ),
        Tool(
            name="pin_telegram_message",
            description="Pins a specific message in a chat. Requires the message_id.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "message_id": {"type": "integer", "description": "ID of the message to pin."}}, "required": ["chat_id", "message_id"]}
        ),
        Tool(
            name="react_to_telegram_message",
            description="Adds an emoji reaction to a message. Requires the message_id.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "message_id": {"type": "integer", "description": "ID of the message to react to."}, "emoji": {"type": "string", "description": "The actual emoji character (e.g., '👍')."}}, "required": ["chat_id", "message_id", "emoji"]}
        ),
        Tool(
            name="forward_telegram_message",
            description="Forwards a message from one chat to another. Requires the from_chat_id, message_id, and to_chat_id.",
            inputSchema={"type": "object", "properties": {"from_chat_id": {"type": ["string", "integer"], "description": "The source chat ID."}, "message_id": {"type": "integer", "description": "The ID of the message to forward."}, "to_chat_id": {"type": ["string", "integer"], "description": "The destination chat ID."}}, "required": ["from_chat_id", "message_id", "to_chat_id"]}
        ),
        Tool(
            name="get_chat_info",
            description="Gets basic information about a chat, user, or bot (like title, exact ID, and type). Useful for verifying a chat_id.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID, username, or phone number."}}, "required": ["chat_id"]}
        ),
        Tool(
            name="get_telegram_chat_member",
            description="Gets detailed information about a specific member inside a group.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "user_id": {"type": "integer", "description": "Numeric ID of the specific user."}}, "required": ["chat_id", "user_id"]}
        ),
        Tool(
            name="set_telegram_chat_title",
            description="Changes the title of a group or channel you admin.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "new_title": {"type": "string", "description": "The new title."}}, "required": ["chat_id", "new_title"]}
        ),
        Tool(
            name="set_telegram_chat_description",
            description="Updates a group's bio/description.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "description": {"type": "string", "description": "The new description text."}}, "required": ["chat_id", "description"]}
        ),
        Tool(
            name="create_telegram_invite_link",
            description="Generates a standard invite link for a group.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}}, "required": ["chat_id"]}
        ),
        Tool(
            name="create_secure_invite_link",
            description="Generates a temporary invite link with an expiration time or member limit.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "expire_minutes": {"type": "integer", "description": "Minutes until link invalidates."}, "member_limit": {"type": "integer", "description": "Max uses of this link."}}, "required": ["chat_id", "expire_minutes"]}
        ),
        Tool(
            name="ban_telegram_member",
            description="Bans a user from a group.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "user_id": {"type": "integer", "description": "User ID to ban."}}, "required": ["chat_id", "user_id"]}
        ),
        Tool(
            name="unban_telegram_member",
            description="Unbans a user from a group.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "user_id": {"type": "integer", "description": "User ID to unban."}}, "required": ["chat_id", "user_id"]}
        ),
        Tool(
            name="promote_telegram_member",
            description="Promotes a member to Admin in a group.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "user_id": {"type": "integer", "description": "User ID to promote."}}, "required": ["chat_id", "user_id"]}
        ),
        Tool(
            name="mark_message_as_read",
            description="Marks messages as read in a chat up to a specific message_id.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "message_id": {"type": "integer", "description": "The ID up to which messages are marked read."}}, "required": ["chat_id", "message_id"]}
        ),
        Tool(
            name="send_animated_message",
            description="Sends a 'magic' animated text message by rapidly editing the text.",
            inputSchema={
                "type": "object", 
                "properties": {
                    "chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, 
                    "final_message": {"type": "string", "description": "The complete message once the animation stops."},
                    "effect": {"type": "string", "enum": ["typewriter", "loading"], "description": "The style of animation."}
                }, 
                "required": ["chat_id", "final_message", "effect"]
            }
        ),
        Tool(
            name="mute_telegram_member",
            description="Mutes a user in a group so they cannot send messages.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "user_id": {"type": "integer", "description": "The User ID to mute."}, "minutes": {"type": "integer", "description": "Duration in minutes (optional for permamute)."}}, "required": ["chat_id", "user_id"]}
        ),
        Tool(
            name="set_telegram_admin_title",
            description="Sets a custom title/rank (e.g., 'CEO') for an admin in a group.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "user_id": {"type": "integer", "description": "The Admin User ID."}, "custom_title": {"type": "string", "description": "The string rank to display next to their name."}}, "required": ["chat_id", "user_id", "custom_title"]}
        ),
        Tool(
            name="set_telegram_chat_photo",
            description="Changes the profile picture of a group or channel.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "photo_path": {"type": "string", "description": "Absolute local file path to the photo."}}, "required": ["chat_id", "photo_path"]}
        ),
        Tool(
            name="manage_chat_join_request",
            description="Approves or declines a user's request to join a private group/channel.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "user_id": {"type": "integer", "description": "The User ID requesting to join."}, "approve": {"type": "boolean", "description": "True to approve, false to decline."}}, "required": ["chat_id", "user_id", "approve"]}
        ),
        Tool(
            name="send_safe_bot_to_bot_message",
            description="Sends a message specifically targeted to another bot.",
            inputSchema={"type": "object", "properties": {"bot_username": {"type": "string", "description": "The exact @username of the bot."}, "message": {"type": "string", "description": "The command or text to send."}}, "required": ["bot_username", "message"]}
        ),
        Tool(
            name="send_business_message",
            description="Attempts to send a message using Telegram Business features.",
            inputSchema={"type": "object", "properties": {"chat_id": {"type": ["string", "integer"], "description": "The target chat ID."}, "message": {"type": "string", "description": "The business message."}}, "required": ["chat_id", "message"]}
        ),
        Tool(
            name="set_bot_menu_button",
            description="Attempts to set the menu button for a bot.",
            inputSchema={"type": "object", "properties": {"bot_username": {"type": "string", "description": "The target bot @username."}, "menu_text": {"type": "string", "description": "The button text."}}, "required": ["bot_username", "menu_text"]}
        ),
        Tool(
            name="register_auto_reply",
            description="Registers a background event listener that automatically replies to incoming messages matching a specific pattern (e.g., commands like '/start').",
            inputSchema={"type": "object", "properties": {"pattern": {"type": "string", "description": "The exact text or regex pattern to trigger the auto-reply (e.g., '/start')."}, "reply_message": {"type": "string", "description": "The text message to automatically send back."}}, "required": ["pattern", "reply_message"]}
        )
    ]
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    try:
        tc = await get_client()
        
        async def resolve_entity():
            chat_id = arguments.get("chat_id")
            if not chat_id:
                raise ValueError("chat_id is required")
            return await get_entity_safely(tc, chat_id)

        # Helper to append queued new messages to any response text
        async def append_new_messages(base_text: str) -> str:
            new_msgs = await get_new_messages_since_last_call()
            return base_text + format_new_messages(new_msgs)

        if name == "send_telegram_message":
            entity = await resolve_entity()
            msg = arguments.get("message")
            sent = await tc.send_message(entity, msg)
            output = await append_new_messages(f"✅ Message sent (ID: {sent.id})")
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "send_telegram_photo":
            entity = await resolve_entity()
            path = arguments.get("photo_path")
            caption = arguments.get("caption", "")
            if not os.path.exists(path):
                return CallToolResult(content=[TextContent(type="text", text=f"❌ File not found: {path}")], isError=True)
            sent = await tc.send_file(entity, path, caption=caption)
            output = await append_new_messages(f"📸 Photo sent (ID: {sent.id})")
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "send_telegram_document":
            entity = await resolve_entity()
            path = arguments.get("document_path")
            caption = arguments.get("caption", "")
            if not os.path.exists(path):
                return CallToolResult(content=[TextContent(type="text", text=f"❌ File not found: {path}")], isError=True)
            sent = await tc.send_file(entity, path, caption=caption, force_document=True)
            output = await append_new_messages(f"📁 Document sent (ID: {sent.id})")
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "send_telegram_video":
            entity = await resolve_entity()
            path = arguments.get("video_path")
            caption = arguments.get("caption", "")
            if not os.path.exists(path):
                return CallToolResult(content=[TextContent(type="text", text=f"❌ File not found: {path}")], isError=True)
            sent = await tc.send_file(entity, path, caption=caption)
            output = await append_new_messages(f"🎥 Video sent (ID: {sent.id})")
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "send_telegram_audio":
            entity = await resolve_entity()
            path = arguments.get("audio_path")
            caption = arguments.get("caption", "")
            if not os.path.exists(path):
                return CallToolResult(content=[TextContent(type="text", text=f"❌ File not found: {path}")], isError=True)
            sent = await tc.send_file(entity, path, caption=caption)
            output = await append_new_messages(f"🎵 Audio sent (ID: {sent.id})")
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "send_telegram_voice":
            entity = await resolve_entity()
            path = arguments.get("voice_path")
            caption = arguments.get("caption", "")
            if not os.path.exists(path):
                return CallToolResult(content=[TextContent(type="text", text=f"❌ File not found: {path}")], isError=True)
            sent = await tc.send_file(entity, path, caption=caption, voice_note=True)
            output = await append_new_messages(f"🎙️ Voice note sent (ID: {sent.id})")
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "send_telegram_animation":
            entity = await resolve_entity()
            path = arguments.get("animation_path")
            caption = arguments.get("caption", "")
            if not os.path.exists(path):
                return CallToolResult(content=[TextContent(type="text", text=f"❌ File not found: {path}")], isError=True)
            sent = await tc.send_file(entity, path, caption=caption)
            output = await append_new_messages(f"🎞️ Animation sent (ID: {sent.id})")
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "send_telegram_media_group":
            entity = await resolve_entity()
            paths = arguments.get("media_paths", [])
            caption = arguments.get("caption", "")
            if not paths:
                return CallToolResult(content=[TextContent(type="text", text="❌ No media paths provided")], isError=True)
            for path in paths:
                if not os.path.exists(path):
                    return CallToolResult(content=[TextContent(type="text", text=f"❌ File not found: {path}")], isError=True)
            sent = await tc.send_file(entity, paths, caption=caption)
            output = await append_new_messages(f"🖼️ Media group sent ({len(paths)} items)")
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "send_telegram_poll":
            entity = await resolve_entity()
            question = arguments.get("question")
            options = arguments.get("options")
            import random
            from telethon.tl.types import InputMediaPoll, Poll, PollAnswer
            
            poll_media = InputMediaPoll(
                poll=Poll(
                    id=random.randint(1, 100000000),
                    hash=0,
                    question=question,
                    answers=[PollAnswer(text=opt, option=bytes([i])) for i, opt in enumerate(options)],
                    closed=False,
                    public_voters=False,
                    multiple_choice=False,
                    quiz=False
                ),
                correct_answers=[]
            )
            sent = await tc.send_message(entity, file=poll_media)
            output = await append_new_messages("📊 Poll sent successfully")
            return CallToolResult(content=[TextContent(type="text", text=output)])

        
        elif name == "send_telegram_location":
            entity = await resolve_entity()
            lat = arguments.get("latitude")
            lon = arguments.get("longitude")
            from telethon.tl.types import InputMediaGeoPoint, InputGeoPoint
            sent = await tc.send_message(entity, file=InputMediaGeoPoint(geo_point=InputGeoPoint(lat=lat, long=lon)))
            output = await append_new_messages("📍 Location sent")
            return CallToolResult(content=[TextContent(type="text", text=output)])

        elif name == "read_telegram_messages":
            entity = await resolve_entity()
            limit = arguments.get("limit", 10)
            messages = await tc.get_messages(entity, limit=limit)
            output_lines = []
            for msg in messages:
                if msg.text or msg.media:
                    media_info = "[Has Media]" if msg.media else ""
                    sender = msg.sender.first_name if msg.sender else "Unknown"
                    text = msg.text[:200] if msg.text else ""
                    output_lines.append(f"{sender} (ID: {msg.id}) {media_info}: {text}")
            base = "Recent Messages:\n" + "\n".join(output_lines)
            output = await append_new_messages(base)
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "edit_telegram_message":
            entity = await resolve_entity()
            msg_id = arguments.get("message_id")
            new_text = arguments.get("new_text")
            await tc.edit_message(entity, msg_id, new_text)
            output = await append_new_messages("✏️ Message edited")
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "delete_telegram_message":
            entity = await resolve_entity()
            msg_id = arguments.get("message_id")
            await tc.delete_messages(entity, msg_id)
            output = await append_new_messages("🗑️ Message deleted")
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "pin_telegram_message":
            entity = await resolve_entity()
            msg_id = arguments.get("message_id")
            await tc.pin_message(entity, msg_id)
            output = await append_new_messages("📌 Message pinned")
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "react_to_telegram_message":
            entity = await resolve_entity()
            msg_id = arguments.get("message_id")
            emoji = arguments.get("emoji")

            free_emojis = await get_free_reactions(client)

            if emoji not in free_emojis:
                return CallToolResult(content=[
                    TextContent(
                        type="text",
                        text=f"❌ '{emoji}' is premium or not allowed.\n\n✅ Free emojis:\n{', '.join(free_emojis)}"
                    )
                ], isError=True)

            from telethon.tl.functions.messages import SendReactionRequest
            from telethon.tl.types import ReactionEmoji

            await tc(SendReactionRequest(
                peer=entity,
                msg_id=msg_id,
                reaction=[ReactionEmoji(emoticon=emoji)]
            ))

            output = await append_new_messages(f"✅ {emoji} Reaction added")
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "forward_telegram_message":
            from_chat_id = arguments.get("from_chat_id")
            to_chat_id = arguments.get("to_chat_id")
            msg_id = arguments.get("message_id")
            from_entity = await get_entity_safely(tc, from_chat_id)
            to_entity = await get_entity_safely(tc, to_chat_id)
            await tc.forward_messages(to_entity, msg_id, from_entity)
            output = await append_new_messages("↪️ Message forwarded")
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "get_chat_info":
            entity = await resolve_entity()
            info = f"Title/Name: {getattr(entity, 'title', getattr(entity, 'first_name', 'Unknown'))}\nID: {entity.id}\nType: {type(entity).__name__}"
            output = await append_new_messages(info)
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "get_telegram_chat_member":
            entity = await resolve_entity()
            user_id = arguments.get("user_id")
            user = await tc.get_entity(user_id)
            info = f"User: {user.first_name} (ID: {user.id})\nUsername: @{user.username if user.username else 'N/A'}"
            output = await append_new_messages(info)
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "set_telegram_chat_title":
            entity = await resolve_entity()
            title = arguments.get("new_title")
            
            if hasattr(entity, 'broadcast') or getattr(entity, 'megagroup', False):
                from telethon.tl.functions.channels import EditTitleRequest
                await tc(EditTitleRequest(channel=entity, title=title))
            else:
                from telethon.tl.functions.messages import EditChatTitleRequest
                await tc(EditChatTitleRequest(chat_id=entity.id, title=title))
                
            output = await append_new_messages("🏷️ Title updated")
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "set_telegram_chat_description":
            entity = await resolve_entity()
            desc = arguments.get("description")
            from telethon.tl.functions.messages import EditChatAboutRequest
            await tc(EditChatAboutRequest(peer=entity, about=desc))
            output = await append_new_messages("📝 Description updated")
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "create_telegram_invite_link":
            entity = await resolve_entity()
            from telethon.tl.functions.messages import ExportChatInviteRequest
            result = await tc(ExportChatInviteRequest(peer=entity))
            output = await append_new_messages(f"🔗 {result.link}")
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "create_secure_invite_link":
            entity = await resolve_entity()
            minutes = arguments.get("expire_minutes")
            limit = arguments.get("member_limit", 0)
            from telethon.tl.functions.messages import ExportChatInviteRequest
            expire_date = int(time.time()) + (minutes * 60)
            result = await tc(ExportChatInviteRequest(
                peer=entity,
                expire_date=expire_date,
                usage_limit=limit if limit > 0 else None
            ))
            output = await append_new_messages(f"🔐 {result.link} (expires in {minutes} min)")
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "ban_telegram_member":
            entity = await resolve_entity()
            user_id = arguments.get("user_id")
            from telethon.tl.functions.channels import EditBannedRequest
            from telethon.tl.types import ChatBannedRights
            await tc(EditBannedRequest(
                channel=entity,
                participant=user_id,
                banned_rights=ChatBannedRights(until_date=None, view_messages=True)
            ))
            output = await append_new_messages(f"🔨 User {user_id} banned")
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "unban_telegram_member":
            entity = await resolve_entity()
            user_id = arguments.get("user_id")
            from telethon.tl.functions.channels import EditBannedRequest
            from telethon.tl.types import ChatBannedRights
            await tc(EditBannedRequest(
                channel=entity,
                participant=user_id,
                banned_rights=ChatBannedRights(until_date=None, view_messages=False)
            ))
            output = await append_new_messages(f"🕊️ User {user_id} unbanned")
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "promote_telegram_member":
            entity = await resolve_entity()
            user_id = arguments.get("user_id")
            from telethon.tl.functions.channels import EditAdminRequest
            from telethon.tl.types import ChatAdminRights
            rights = ChatAdminRights(
                change_info=True, post_messages=True, edit_messages=True,
                delete_messages=True, ban_users=True, invite_users=True,
                pin_messages=True, add_admins=False, anonymous=False, manage_call=True
            )
            await tc(EditAdminRequest(channel=entity, user_id=user_id, admin_rights=rights, rank="Admin"))
            output = await append_new_messages(f"⭐ User {user_id} promoted")
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "download_telegram_media":
            entity = await resolve_entity()
            msg_id = arguments.get("message_id")
            save_path = arguments.get("save_path", "/tmp/telegram_download")
            msg = await tc.get_messages(entity, ids=msg_id)
            if msg and msg.media:
                downloaded_path = await tc.download_media(msg, save_path)
                output = await append_new_messages(f"📥 Downloaded to {downloaded_path}")
                return CallToolResult(content=[TextContent(type="text", text=output)])
            return CallToolResult(content=[TextContent(type="text", text="❌ No media found")], isError=True)
        
        elif name == "get_dialog_list":
            limit = arguments.get("limit", 20)
            dialogs = await tc.get_dialogs(limit=limit)
            lines = [f"{d.name} (ID: {d.id}): {d.message.text[:50] if d.message and d.message.text else 'No text'}" for d in dialogs]
            base = "Dialogs:\n" + "\n".join(lines)
            output = await append_new_messages(base)
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        elif name == "send_animated_message":
            entity = await resolve_entity()
            final_message = arguments.get("final_message")
            effect = arguments.get("effect", "typewriter")
            
            if effect == "loading":
                frames = ["🔄 Loading.", "🔄 Loading..", "🔄 Loading...", "🔄 Loading....", f"✅ {final_message}"]
            elif effect == "typewriter":
                frames = [final_message[:i] + "█" for i in range(1, len(final_message))]
                frames.append(final_message)
                
            sent = await tc.send_message(entity, frames[0])
            for frame in frames[1:]:
                await asyncio.sleep(0.3)
                await tc.edit_message(entity, sent.id, frame)
                
            output = await append_new_messages(f"✨ Magic animated message sent (ID: {sent.id})")
            return CallToolResult(content=[TextContent(type="text", text=output)])

    
        elif name == "mute_telegram_member":
            entity = await resolve_entity()
            user_id = arguments.get("user_id")
            minutes = arguments.get("minutes")
            
            from telethon.tl.functions.channels import EditBannedRequest
            from telethon.tl.types import ChatBannedRights
            
            until_date = int(time.time()) + (minutes * 60) if minutes else None
            rights = ChatBannedRights(until_date=until_date, send_messages=True)
            
            await tc(EditBannedRequest(channel=entity, participant=user_id, banned_rights=rights))
            mute_time = f"for {minutes} minutes" if minutes else "permanently"
            output = await append_new_messages(f"🔇 User {user_id} muted {mute_time}")
            return CallToolResult(content=[TextContent(type="text", text=output)])

        elif name == "set_telegram_admin_title":
            entity = await resolve_entity()
            user_id = arguments.get("user_id")
            custom_title = arguments.get("custom_title")
            
            from telethon.tl.functions.channels import EditAdminRequest
            from telethon.tl.types import ChatAdminRights
            
            rights = ChatAdminRights(change_info=True, post_messages=True, edit_messages=True, delete_messages=True, ban_users=True, invite_users=True, pin_messages=True, manage_call=True)
            await tc(EditAdminRequest(channel=entity, user_id=user_id, admin_rights=rights, rank=custom_title))
            output = await append_new_messages(f"👑 Admin title for {user_id} set to '{custom_title}'")
            return CallToolResult(content=[TextContent(type="text", text=output)])

        elif name == "set_telegram_chat_photo":
            entity = await resolve_entity()
            path = arguments.get("photo_path")
            
            if not os.path.exists(path):
                return CallToolResult(content=[TextContent(type="text", text=f"❌ File not found: {path}")], isError=True)
            
            uploaded = await tc.upload_file(path)
            from telethon.tl.functions.channels import EditPhotoRequest
            from telethon.tl.types import InputChatUploadedPhoto
            
            await tc(EditPhotoRequest(channel=entity, photo=InputChatUploadedPhoto(file=uploaded)))
            output = await append_new_messages("🖼️ Chat photo updated successfully")
            return CallToolResult(content=[TextContent(type="text", text=output)])

        elif name == "manage_chat_join_request":
            entity = await resolve_entity()
            user_id = arguments.get("user_id")
            approve = arguments.get("approve")
            
            from telethon.tl.functions.messages import HideChatJoinRequestRequest
            await tc(HideChatJoinRequestRequest(peer=entity, user_id=user_id, approved=approve))
            action = "Approved" if approve else "Declined"
            output = await append_new_messages(f"✅ {action} join request for user {user_id}")
            return CallToolResult(content=[TextContent(type="text", text=output)])

        elif name == "send_safe_bot_to_bot_message":
            bot_username = arguments.get("bot_username")
            msg = arguments.get("message")
            bot_entity = await get_entity_safely(tc, bot_username)
            sent = await tc.send_message(bot_entity, msg)
            output = await append_new_messages(f"🤖 Safe message sent to {bot_username} (ID: {sent.id})")
            return CallToolResult(content=[TextContent(type="text", text=output)])

        elif name == "send_business_message":
            entity = await resolve_entity()
            msg = arguments.get("message")
            sent = await tc.send_message(entity, f"[Business Message] {msg}")
            output = await append_new_messages(f"💼 Business message sent (ID: {sent.id})")
            return CallToolResult(content=[TextContent(type="text", text=output)])


        elif name == "register_auto_reply":
            pattern = arguments.get("pattern")
            reply_message = arguments.get("reply_message")
            
            from telethon import events
            from telethon.tl.types import PeerUser, PeerChat, PeerChannel

            @tc.on(events.NewMessage(pattern=pattern))
            async def auto_reply_handler(event):
                chat_id = event.message.peer_id
                if isinstance(chat_id, (PeerUser, PeerChat, PeerChannel)):
                    await event.reply(reply_message)
                    
            output = await append_new_messages(f"🤖 Background listener successfully registered! Automatically replying to '{pattern}' with: '{reply_message}'")
            return CallToolResult(content=[TextContent(type="text", text=output)])


        elif name == "set_bot_menu_button":
            # Very likely to fail for User Accounts, but structure provided to prevent crashing
            return CallToolResult(content=[TextContent(type="text", text="⚠️ set_bot_menu_button is restricted by Telegram for User Accounts. Use @BotFather to configure bot UI.")], isError=True)

        elif name == "mark_message_as_read":
            entity = await resolve_entity()
            msg_id = arguments.get("message_id")
            await tc.send_read_acknowledge(entity, max_id=msg_id)
            output = await append_new_messages("✅ Marked as read")
            return CallToolResult(content=[TextContent(type="text", text=output)])
        
        else:
            return CallToolResult(content=[TextContent(type="text", text=f"Unknown tool: {name}")], isError=True)
            
    except Exception as e:
        return CallToolResult(content=[TextContent(type="text", text=f"Error: {str(e)}")], isError=True)

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
