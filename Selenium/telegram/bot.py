import time
from collections import deque
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, ChatJoinRequestHandler

# Yahan apna BotFather wala token daalo
TOKEN = "8666398252:AAFnBdxKkpOD_eITcHYRoFIqJw4OQ6mOgNQ"

# --- MEMORY FOR LOOP PREVENTION ---
# Stores timestamps of our replies to specific bots. Format: {bot_id: deque([timestamps])}
bot_interaction_memory = {}
B2B_RATE_LIMIT = 3        # Ek specific bot ko max 3 baar reply karega
B2B_TIME_WINDOW = 60      # 60 seconds ki window me

async def greet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Original Greet function with Fire Heart effect."""
    HEART_FIRE_EFFECT_ID = "5104841245755180586"
    await update.message.reply_text("❤️‍🔥", message_effect_id=HEART_FIRE_EFFECT_ID)

async def b2b_guardian_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles messages coming from OTHER bots, with strict infinite loop protection."""
    # Agar message nahi hai ya sender bot nahi hai, toh aage badho
    if not update.message or not update.message.from_user.is_bot:
        return

    sender_bot_id = update.message.from_user.id
    current_time = time.time()

    # Initialize or clean up old timestamps for this bot
    if sender_bot_id not in bot_interaction_memory:
        bot_interaction_memory[sender_bot_id] = deque()

    # Time window se purane timestamps hata do
    while bot_interaction_memory[sender_bot_id] and current_time - bot_interaction_memory[sender_bot_id][0] > B2B_TIME_WINDOW:
        bot_interaction_memory[sender_bot_id].popleft()

    # Rate Limit Check: Loop detect ho gaya
    if len(bot_interaction_memory[sender_bot_id]) >= B2B_RATE_LIMIT:
        print(f"🛡️ [B2B RATE LIMIT] Ignoring bot {sender_bot_id} to prevent infinite loop.")
        return

    # Interaction record karo
    bot_interaction_memory[sender_bot_id].append(current_time)

    # Example B2B Reaction: Kisi dusre bot ne kuch bheja toh usko acknowledge karo
    text = update.message.text
    if text:
        await update.message.reply_text(f"🤖 Inter-Bot Link Establised. Read: {text[:15]}...")

async def business_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles messages sent to your personal account via Business Mode."""
    # Telegram tumhare behalf par ye bheja jayega
    if update.business_message:
        await context.bot.send_message(
            chat_id=update.business_message.chat_id,
            text="⚡ Automated Business Reply: Currently processing operations. Will get back to you shortly.",
            business_connection_id=update.business_message.business_connection_id
        )

async def auto_approve_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin Tool: Automatically approves join requests for your groups."""
    request = update.chat_join_request
    user_name = request.from_user.first_name
    await request.approve()
    print(f"✅ Auto-approved join request from {user_name}")

async def create_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin Tool: Creates a new forum topic in a supergroup."""
    if not update.message.chat.is_forum:
        await update.message.reply_text("❌ This command only works in Forum Supergroups.")
        return

    topic_name = " ".join(context.args) if context.args else f"Log Thread {int(time.time())[-4:]}"
    try:
        topic = await context.bot.create_forum_topic(chat_id=update.message.chat_id, name=topic_name)
        await update.message.reply_text(f"📁 Topic '{topic_name}' created! ID: {topic.message_thread_id}")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to create topic: {e}")

if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()

    # Base Commands
    app.add_handler(CommandHandler("greet", greet_callback))

    # Admin Commands
    app.add_handler(CommandHandler("createtopic", create_topic))

    # Auto-Approve Join Requests (Admin Right required)
    app.add_handler(ChatJoinRequestHandler(auto_approve_join))

    # Business Mode Handler
    app.add_handler(MessageHandler(filters.UpdateType.BUSINESS_MESSAGES, business_message_handler))

    # B2B Shield Handler (Catches all text from other bots)
    app.add_handler(MessageHandler(filters.TEXT & filters.User(is_bot=True), b2b_guardian_handler))

    print("🚀 Advanced Tactical Bot is running... Press Ctrl+C to stop.")
    app.run_polling()
