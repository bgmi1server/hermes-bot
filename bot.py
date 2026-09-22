import logging
import httpx
import asyncio
import time
import re
from telegram import Update, BotCommand, BotCommandScopeDefault, BotCommandScopeChat, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
try:
    from config import (
        BOT_TOKEN, ADMIN_ID, GUEST_IDS,
        get_provider_info, get_next_model,
        AVAILABLE_MODELS, DEFAULT_MODEL, TAVILY_API_KEY
    )
except ImportError:
    raise ImportError("Please create a config.py file with necessary configurations.")

# ==========================================
# Logging Configuration
# ==========================================
import logging.handlers
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler('bot.log', maxBytes=1024*1024, backupCount=2, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Global State
user_models = {}  # {user_id: model_name}
user_modes = {}   # {user_id: mode_name}
maintenance_mode = False
banned_users = set()

# Global HTTP client for connection pooling (speeds up requests)
http_client = httpx.AsyncClient(timeout=120.0)

import json
import os
import urllib.request
import urllib.error

# ==========================================
# Dynamic User Management (GitHub Issue DB)
# ==========================================
def _load_authorized_users() -> tuple[set, set]:
    """Load dynamically added users and banned users from GitHub Issue #1."""
    try:
        from config import GITHUB_PAT
        if not GITHUB_PAT:
            return set(), set()
        req = urllib.request.Request("https://api.github.com/repos/bgmi1server/hermes-bot/issues/1")
        req.add_header("Authorization", f"token {GITHUB_PAT}")
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("User-Agent", "HermesBot")
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            body_json = json.loads(data.get("body", '{"users": [], "banned": []}'))
            return set(body_json.get("users", [])), set(body_json.get("banned", []))
    except Exception as e:
        logger.error(f"Failed to load DB from GitHub: {e}")
    return set(), set()

def _save_authorized_users() -> None:
    """Persist the current dynamic user set and banned list to GitHub Issue #1."""
    try:
        from config import GITHUB_PAT
        if not GITHUB_PAT:
            return
        
        body_content = json.dumps({
            "users": list(authorized_users - set(GUEST_IDS)),
            "banned": list(banned_users)
        })
        payload = json.dumps({"body": body_content}).encode('utf-8')
        
        req = urllib.request.Request("https://api.github.com/repos/bgmi1server/hermes-bot/issues/1", data=payload, method="PATCH")
        req.add_header("Authorization", f"token {GITHUB_PAT}")
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("User-Agent", "HermesBot")
        with urllib.request.urlopen(req, timeout=10) as response:
            pass
    except Exception as e:
        logger.error(f"Failed to save DB to GitHub: {e}")

# In-memory sets
_db_users, _db_banned = _load_authorized_users()
authorized_users: set = set(GUEST_IDS) | _db_users
banned_users.update(_db_banned)

async def check_access(update: Update) -> bool:
    user = update.effective_user
    if user.id == ADMIN_ID:
        return True
    if user.id in banned_users:
        await update.message.reply_text("🚫 You have been banned from using this bot.")
        return False
    if maintenance_mode:
        await update.message.reply_text("🔧 The bot is currently undergoing maintenance. Please try again later.")
        return False
    if user.id not in authorized_users:
        await update.message.reply_text("⛔ Unauthorized access. You are not on the guest list.")
        return False
    return True

# ==========================================
# Command Handlers
# ==========================================
async def send_long_message(update: Update, text: str, status_msg=None, parse_mode=None):
    """Safely split and send messages that exceed Telegram's 4096 char limit."""
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for i, chunk in enumerate(chunks):
        if i == 0 and status_msg:
            try:
                await status_msg.edit_text(chunk, parse_mode=parse_mode)
            except Exception:
                await status_msg.edit_text(chunk)
        else:
            try:
                await update.message.reply_text(chunk, parse_mode=parse_mode)
            except Exception:
                await update.message.reply_text(chunk)

async def notify_admin_error(context: ContextTypes.DEFAULT_TYPE, location: str, error: Exception) -> None:
    if ADMIN_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🚨 **Critical Error Alert**\n\n**Location:** `{location}`\n**Error:** `{error}`",
                parse_mode='Markdown'
            )
        except Exception:
            pass
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not await check_access(update):
        return

    user_model = user_models.get(user.id, DEFAULT_MODEL)
    welcome_msg = (
        f"Hello {user.first_name}! I am Hermes, your AI assistant.\n\n"
        f"Currently using model: {user_model}\n\n"
        "You can chat with me directly, use /search to find information, or use /imagine to generate images!"
    )
    await update.message.reply_text(welcome_msg)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not await check_access(update):
        return

    user_model = user_models.get(user.id, DEFAULT_MODEL)
    help_msg = (
        "Available Commands:\n"
        "/start - Start interacting with the bot\n"
        "/help - Show this help message\n"
        "/search <query> - Search DuckDuckGo for the given query\n"
        "/imagine <prompt> - Generate an image using Grok\n"
        "/model - List available models or switch model (/model <name>)\n\n"
        f"Current model: {user_model}\n"
        "Just type any message to chat!"
    )
    await update.message.reply_text(help_msg)

async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not await check_access(update):
        return

    user_model = user_models.get(user.id, DEFAULT_MODEL)
    if not context.args:
        models_str = "\n".join([f"- {m}" for m in AVAILABLE_MODELS])
        await update.message.reply_text(
            f"Currently using: {user_model}\n\nAvailable models:\n- auto (Round-robin across all)\n{models_str}\n\n"
            "To switch, use: /model <model_name> or /model auto"
        )
        return

    requested_model = context.args[0]
    if requested_model == "auto" or requested_model in AVAILABLE_MODELS:
        user_models[user.id] = requested_model
        await update.message.reply_text(f"Successfully switched to model: {requested_model}")
    else:
        await update.message.reply_text(f"Invalid model. Please choose 'auto' or from the available models.")

MODES_INFO = {
    "default": "🤖 Standard AI Assistant",
    "study": "🎓 Professor (Forces reliable models, detailed explanations)",
    "coder": "💻 Senior Dev (Forces Poolside model, strict code formatting)",
    "creative": "🎨 Writer (Forces 70B+ models, highly imaginative)",
    "concise": "⚡ Quick (Answers in 1-2 sentences)"
}

async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not await check_access(update):
        return

    user_mode = user_modes.get(user.id, "default")
    
    if not context.args:
        # Build inline keyboard for modes
        keyboard = []
        for m, desc in MODES_INFO.items():
            keyboard.append([InlineKeyboardButton(f"{desc.split()[0]} {m.capitalize()}", callback_data=f"mode_{m}")])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Currently using mode: *{user_mode}*\n\nSelect a new mode below:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return

    requested_mode = context.args[0].lower()
    if requested_mode in MODES_INFO:
        user_modes[user.id] = requested_mode
        await update.message.reply_text(f"Successfully switched to mode: *{requested_mode}* {MODES_INFO[requested_mode].split()[0]}", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"Invalid mode. Please choose from: {', '.join(MODES_INFO.keys())}")

async def mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = query.from_user
    
    if user.id not in authorized_users and user.id != ADMIN_ID:
        await query.answer("Unauthorized.", show_alert=True)
        return
        
    await query.answer()
    
    requested_mode = query.data.replace("mode_", "")
    if requested_mode in MODES_INFO:
        user_modes[user.id] = requested_mode
        await query.edit_message_text(
            f"Successfully switched to mode: *{requested_mode}* {MODES_INFO[requested_mode].split()[0]}",
            parse_mode='Markdown'
        )

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not await check_access(update):
        return

    query = " ".join(context.args) if context.args else None
    
    if not query:
        await update.message.reply_text("Please provide a search query. Usage: /search <your query>")
        return

    await update.message.reply_chat_action("typing")
    
    try:
        tavily_payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "basic",
            "include_answer": False,
            "max_results": 3
        }
        resp = await http_client.post("https://api.tavily.com/search", json=tavily_payload, timeout=10.0)
        resp.raise_for_status()
        
        data = resp.json()
        results = data.get('results', [])
        
        if results:
            formatted_results = []
            for r in results:
                title = r.get('title', 'No Title')
                url = r.get('url', 'No URL')
                content = r.get('content', 'No snippet available.')
                formatted_results.append(f"🔹 {title}\n🔗 {url}\n📝 {content}")
                
            response_text = f"Search results for '{query}':\n\n" + "\n\n".join(formatted_results)
            await update.message.reply_text(response_text)
        else:
            await update.message.reply_text("No results found for your query.")
            
    except Exception as e:
        logger.error(f"Error during Tavily search: {e}")
        await update.message.reply_text("An error occurred while searching. Please try again later.")

# ==========================================
# User Management Commands (Admin only)
# ==========================================
async def adduser_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ This command is for admins only.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /adduser <telegram_user_id>")
        return

    new_id = int(context.args[0])
    if new_id in authorized_users:
        await update.message.reply_text(f"✅ User `{new_id}` is already authorized.", parse_mode='Markdown')
        return

    authorized_users.add(new_id)
    _save_authorized_users()
    await update.message.reply_text(f"✅ User `{new_id}` has been added and can now use the bot.", parse_mode='Markdown')
    logger.info(f"Admin added user {new_id}")

async def removeuser_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ This command is for admins only.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /removeuser <telegram_user_id>")
        return

    rem_id = int(context.args[0])
    if rem_id not in authorized_users:
        await update.message.reply_text(f"⚠️ User `{rem_id}` is not in the authorized list.", parse_mode='Markdown')
        return

    authorized_users.discard(rem_id)
    _save_authorized_users()
    await update.message.reply_text(f"🚫 User `{rem_id}` has been removed.", parse_mode='Markdown')
    logger.info(f"Admin removed user {rem_id}")

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ This command is for admins only.")
        return

    if not authorized_users:
        await update.message.reply_text("No guest users authorized yet. Use /adduser <id> to add one.")
        return

    user_list = "\n".join([f"• `{uid}`" for uid in sorted(authorized_users)])
    await update.message.reply_text(
        f"👥 *Authorized Users* ({len(authorized_users)} total)\n\n{user_list}",
        parse_mode='Markdown'
    )

async def maintenance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global maintenance_mode
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    maintenance_mode = not maintenance_mode
    state = "ON" if maintenance_mode else "OFF"
    await update.message.reply_text(f"🔧 Maintenance mode is now *{state}*.", parse_mode='Markdown')

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Usage: /ban <user_id>")
        return
    try:
        b_id = int(context.args[0])
        banned_users.add(b_id)
        if b_id in authorized_users:
            authorized_users.discard(b_id)
        _save_authorized_users()
        await update.message.reply_text(f"🔨 User `{b_id}` has been permanently banned.", parse_mode='Markdown')
    except ValueError:
        await update.message.reply_text("Invalid user ID.")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Usage: /unban <user_id>")
        return
    try:
        b_id = int(context.args[0])
        if b_id in banned_users:
            banned_users.discard(b_id)
            _save_authorized_users()
            await update.message.reply_text(f"🕊️ User `{b_id}` has been unbanned.", parse_mode='Markdown')
        else:
            await update.message.reply_text("User is not banned.")
    except ValueError:
        await update.message.reply_text("Invalid user ID.")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    message = " ".join(context.args)
    success = 0
    await update.message.reply_text(f"📢 Broadcasting to {len(authorized_users)} users...")
    
    for uid in authorized_users:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 **Announcement from Admin:**\n\n{message}", parse_mode='Markdown')
            success += 1
        except Exception:
            pass
            
    await update.message.reply_text(f"✅ Broadcast sent to {success}/{len(authorized_users)} users.")

bot_start_time = time.time()

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
        
    uptime_seconds = int(time.time() - bot_start_time)
    m, s = divmod(uptime_seconds, 60)
    h, m = divmod(m, 60)
    uptime_str = f"{h}h {m}m {s}s"
    
    stats_text = (
        "📊 **Bot Statistics**\n\n"
        f"⏱️ Uptime: `{uptime_str}`\n"
        f"👥 Users: `{len(authorized_users)}`\n"
        f"🚫 Banned: `{len(banned_users)}`\n"
        f"🤖 Models: `{len(AVAILABLE_MODELS)}`\n"
        f"🔧 Maintenance: `{'ON' if maintenance_mode else 'OFF'}`"
    )
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def clearhistory_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Usage: /clearhistory <user_id>")
        return
    try:
        t_id = int(context.args[0])
        if t_id in chat_histories:
            chat_histories[t_id] = []
            await update.message.reply_text(f"🧹 History cleared for `{t_id}`.", parse_mode='Markdown')
        else:
            await update.message.reply_text("No history found for that user.")
    except ValueError:
        await update.message.reply_text("Invalid user ID.")

async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
        
    try:
        with open('bot.log', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            last_lines = "".join(lines[-30:])
            if not last_lines.strip():
                last_lines = "Log file is empty."
            await update.message.reply_text(f"📜 **System Logs (Last 30 lines):**\n```\n{last_lines}\n```", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to read logs: {e}")
async def imagine_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not await check_access(update):
        return

    prompt = " ".join(context.args) if context.args else None
    
    if not prompt:
        await update.message.reply_text("Please provide a prompt. Usage: /imagine <your prompt>")
        return

    status_msg = await update.message.reply_text(f"✨ Enhancing your prompt with AI...")
    
    # --- Step 1: AI Prompt Enhancement ---
    user_model = user_models.get(user.id, DEFAULT_MODEL)
    model_to_use = get_next_model() if user_model == "auto" else user_model
    base_url, api_key, extra_headers = get_provider_info(model_to_use)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "HermesTelegramBot/1.0",
        **extra_headers
    }
    enhance_payload = {
        "model": model_to_use,
        "messages": [
            {"role": "system", "content": "You are an expert AI image prompt engineer. Your ONLY job is to take a user's simple idea and rewrite it as a single, richly detailed, photorealistic image generation prompt. Include: art style, lighting, camera angle, mood, quality tags (e.g. 8K, ultra-detailed, cinematic). Output ONLY the final prompt text, with NO extra commentary, NO quotes, NO labels."},
            {"role": "user", "content": f"Enhance this prompt: {prompt}"}
        ]
    }
    
    enhanced_prompt = prompt  # fallback to original if LLM fails
    try:
        enhance_resp = await http_client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=enhance_payload,
            timeout=30.0
        )
        enhance_resp.raise_for_status()
        enhanced_prompt = enhance_resp.json()['choices'][0]['message']['content'].strip()
        logger.info(f"Prompt enhanced: {enhanced_prompt}")
    except Exception as e:
        logger.warning(f"Prompt enhancement failed, using original: {e}")

    # --- Step 2: Generate with flux-pro on Pollinations ---
    import urllib.parse
    import random
    
    # Cap enhanced prompt at 400 chars to avoid URL-too-long errors
    if len(enhanced_prompt) > 400:
        enhanced_prompt = enhanced_prompt[:400]
    
    encoded_prompt = urllib.parse.quote(enhanced_prompt)
    seed = random.randint(1, 1000000)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model=flux-pro&width=1024&height=1024&seed={seed}&nologo=true&enhance=true"
    
    await status_msg.edit_text(f"🎨 Generating HD image... [0s]")
    start_time = time.time()

    async def update_timer():
        try:
            while True:
                await asyncio.sleep(2)
                elapsed = int(time.time() - start_time)
                try:
                    await status_msg.edit_text(f"🎨 Generating HD image... [{elapsed}s]")
                except Exception:
                    pass
        except asyncio.CancelledError:
            pass

    timer_task = asyncio.create_task(update_timer())
    
    try:
        response = await http_client.get(image_url, timeout=120.0, follow_redirects=True)
        response.raise_for_status()
        image_bytes = response.content
        
        timer_task.cancel()
        elapsed_total = int(time.time() - start_time)
            
    except Exception as e:
        timer_task.cancel()
        logger.error(f"Error generating image: {e}")
        await status_msg.edit_text("❌ An error occurred while generating the image. Please try again later.")
        return

    try:
        # Send the photo back to Telegram with the prompt as the caption
        caption_text = f"Prompt: {prompt}"
        if len(caption_text) > 1000:
            caption_text = caption_text[:1000] + "..."
        await update.message.reply_photo(photo=image_bytes, caption=caption_text)
        await status_msg.delete()
    except Exception as e:
        logger.error(f"Error sending photo to Telegram: {e}")
        try:
            await status_msg.edit_text("❌ Failed to send the image to Telegram. It might be too large.")
        except:
            pass


import re

def parse_markdown_to_html(text):
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r'```(?:.*?)\n(.*?)```', r'<pre>\1</pre>', text, flags=re.DOTALL)
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    return text

# ==========================================
# YouTube Summarizer
# ==========================================
async def summarize_youtube(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str) -> None:
    """Auto-triggered when a YouTube URL is detected in a message."""
    if not await check_access(update):
        return

    status_msg = await update.message.reply_text("🎬 Fetching video transcript...")

    try:
        from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
        import re as _re2

        # Extract video ID
        vid_match = _re2.search(r'(?:v=|shorts/|youtu\.be/)([\w\-]{11})', url)
        if not vid_match:
            await status_msg.edit_text("❌ Couldn't extract video ID from that URL.")
            return

        video_id = vid_match.group(1)

        # Fetch transcript
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        except (NoTranscriptFound, TranscriptsDisabled):
            await status_msg.edit_text("❌ This video doesn't have a transcript available. Try a different video.")
            return

        # Join transcript text and cap at 12,000 chars to avoid LLM overflow
        full_text = " ".join([t['text'] for t in transcript_list])
        if len(full_text) > 12000:
            full_text = full_text[:12000] + "..."

        await status_msg.edit_text("🧠 Summarizing...")

        # Ask the LLM to summarize
        user_model = user_models.get(update.effective_user.id, DEFAULT_MODEL)
        model_to_use = get_next_model() if user_model == "auto" else user_model
        base_url, api_key, extra_headers = get_provider_info(model_to_use)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "HermesTelegramBot/1.0",
            **extra_headers
        }
        payload = {
            "model": model_to_use,
            "messages": [
                {"role": "system", "content": "You are an expert at summarizing YouTube video transcripts. Create a concise, well-structured summary with: a bold title, key points as bullet points, and a brief conclusion. Be clear and informative."},
                {"role": "user", "content": f"Summarize this YouTube video transcript:\n\n{full_text}"}
            ]
        }
        resp = await http_client.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=60.0)
        resp.raise_for_status()
        summary = resp.json()['choices'][0]['message']['content'].strip()
        formatted = parse_markdown_to_html(summary)

        await status_msg.delete()
        try:
            await update.message.reply_text(f"🎬 <b>YouTube Summary</b>\n🔗 {url}\n\n{formatted}", parse_mode='HTML')
        except Exception:
            await update.message.reply_text(f"🎬 YouTube Summary\n🔗 {url}\n\n{summary}")

    except ImportError:
        await status_msg.edit_text("❌ YouTube transcript library not installed. Run: pip install youtube-transcript-api")
    except Exception as e:
        logger.error(f"YouTube summarizer error: {e}")
        await status_msg.edit_text("❌ Failed to summarize this video. It may be unavailable or region-locked.")


# ==========================================
# Document Summarizer
# ==========================================
async def summarize_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Triggered when user sends any document/file to the bot."""
    user = update.effective_user
    if not await check_access(update):
        return

    doc = update.message.document
    file_name = doc.file_name or "document"
    mime_type = doc.mime_type or ""

    # Supported types
    supported_ext = ['.txt', '.md', '.py', '.js', '.csv', '.json', '.html', '.pdf']
    is_supported = any(file_name.lower().endswith(ext) for ext in supported_ext) or 'text' in mime_type or 'pdf' in mime_type

    if not is_supported:
        await update.message.reply_text(
            f"📎 I can't read *{file_name}* — I support: PDF, TXT, MD, PY, JS, CSV, JSON, HTML.\nSend one of those for a summary!",
            parse_mode='Markdown'
        )
        return

    status_msg = await update.message.reply_text(f"📄 Reading *{file_name}*...", parse_mode='Markdown')

    try:
        # Download the file
        tg_file = await context.bot.get_file(doc.file_id)
        file_bytes = await tg_file.download_as_bytearray()

        # Extract text
        extracted_text = ""
        if file_name.lower().endswith('.pdf') or 'pdf' in mime_type:
            try:
                import fitz  # PyMuPDF
                pdf_doc = fitz.open(stream=bytes(file_bytes), filetype="pdf")
                extracted_text = "\n".join([page.get_text() for page in pdf_doc])
            except ImportError:
                await status_msg.edit_text("❌ PDF support not installed. Run: pip install PyMuPDF")
                return
        else:
            # Text-based file — decode it
            for enc in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    extracted_text = file_bytes.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue

        if not extracted_text.strip():
            await status_msg.edit_text("❌ Couldn't extract any text from that file.")
            return

        # Cap at 15,000 chars
        if len(extracted_text) > 15000:
            extracted_text = extracted_text[:15000] + "\n\n[... content truncated ...]"

        await status_msg.edit_text(f"🧠 Summarizing *{file_name}*...", parse_mode='Markdown')

        user_model = user_models.get(user.id, DEFAULT_MODEL)
        model_to_use = get_next_model() if user_model == "auto" else user_model
        base_url, api_key, extra_headers = get_provider_info(model_to_use)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "HermesTelegramBot/1.0",
            **extra_headers
        }
        payload = {
            "model": model_to_use,
            "messages": [
                {"role": "system", "content": "You are an expert document analyst. Summarize the provided document with: a bold title, key points as bullet points, and a brief conclusion. Be concise and accurate."},
                {"role": "user", "content": f"Summarize this document ({file_name}):\n\n{extracted_text}"}
            ]
        }
        resp = await http_client.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=60.0)
        resp.raise_for_status()
        summary = resp.json()['choices'][0]['message']['content'].strip()
        formatted = parse_markdown_to_html(summary)

        await status_msg.delete()
        try:
            await update.message.reply_text(f"📄 <b>Summary: {file_name}</b>\n\n{formatted}", parse_mode='HTML')
        except Exception:
            await update.message.reply_text(f"📄 Summary: {file_name}\n\n{summary}")

    except Exception as e:
        logger.error(f"Document summarizer error: {e}")
        await status_msg.edit_text("❌ An error occurred while reading your document. Please try again.")


# ==========================================
# Intent Classifier (Smart RAG)
# ==========================================
async def check_needs_web_search(query: str) -> bool:
    """Uses a fast LLM check to decide if a query needs real-time web search."""
    import re as _re
    # Fast local rejections to save latency
    if len(query.split()) < 3 and not "?" in query:
        return False
    
    ignore_phrases = ["hello", "hi", "hey", "how are you", "what are you", "who are you", "thanks", "thank you", "bye"]
    if any(query.lower().strip('?.,! ') == p for p in ignore_phrases):
        return False

    is_math = bool(_re.fullmatch(r'^[0-9\s\+\-\*\/\(\)\=\.a-zA-Z]+\??$', query))
    if is_math and len(query.split()) <= 4:
        return False

    # Ask the LLM (using the current rotation)
    try:
        model_to_use = get_next_model() if current_model == "auto" else current_model
        base_url, api_key, extra_headers = get_provider_info(model_to_use)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "HermesTelegramBot/1.0",
            **extra_headers
        }
        payload = {
            "model": model_to_use,
            "messages": [
                {"role": "system", "content": "You are a web-search intent classifier. Does the user's message require searching the live internet to answer accurately?\nYou MUST answer YES if the user asks about:\n- Recent events, news, or current dates\n- New AI models, products, or software releases (e.g., GPT-5, GPT-6, new iPhones)\n- Live data (weather, sports, stocks)\n- Queries like 'What is the latest...' or 'Do you know about...'\nAnswer ONLY with exactly YES or NO."},
                {"role": "user", "content": query}
            ],
            "max_tokens": 5,
            "temperature": 0.0
        }
        resp = await http_client.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=5.0)
        resp.raise_for_status()
        reply = resp.json()['choices'][0]['message']['content'].strip().upper()
        return "YES" in reply
    except Exception as e:
        logger.error(f"Intent Classifier failed: {e}")
        return False

# ==========================================
# Message Handler (Chatting with LLM)
# ==========================================
chat_histories = {}
MAX_HISTORY = 10
async def chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE, voice_text: str = None) -> None:
    user = update.effective_user
    if not await check_access(update):
        return

    user_message = voice_text if voice_text else update.message.text
    if not user_message:
        return
        
    user_model = user_models.get(user.id, DEFAULT_MODEL)
    active_mode = user_modes.get(user.id, "default")
    
    if active_mode == "study":
        model_to_use = "llama-3.3-70b-versatile"
    elif active_mode == "coder":
        model_to_use = "poolside/laguna-s-2.1"
    elif active_mode == "creative":
        model_to_use = "nvidia/nemotron-3-super-120b-a12b:free"
    else:
        model_to_use = get_next_model() if user_model == "auto" else user_model
        
    # Check if this is a reply to a generated image (Image modification request)
    if update.message.reply_to_message and update.message.reply_to_message.photo:
        old_caption = update.message.reply_to_message.caption
        if old_caption and old_caption.startswith("Prompt: "):
            original_prompt = old_caption[8:]
            
            status_msg = await update.message.reply_text("🧠 Merging prompts...")
            base_url, api_key, extra_headers = get_provider_info(model_to_use)
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                **extra_headers
            }
            
            rewrite_payload = {
                "model": model_to_use,
                "messages": [
                    {"role": "system", "content": "You are a prompt engineering assistant. The user has an original image prompt and wants to modify it. Return ONLY the new, combined, highly detailed image generation prompt. Do not include any conversational text."},
                    {"role": "user", "content": f"Original prompt: {original_prompt}\n\nUser's requested change: {user_message}"}
                ]
            }
            
            try:
                rewrite_resp = await http_client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=rewrite_payload
                )
                rewrite_resp.raise_for_status()
                new_prompt = rewrite_resp.json()['choices'][0]['message']['content'].strip()
                
                await status_msg.delete()
                context.args = new_prompt.split()
                await imagine_command(update, context)
                return
            except Exception as e:
                logger.error(f"Error rewriting prompt: {e}")
                await status_msg.edit_text("Error rewriting prompt. Please try again.")
                return

    # Store original message BEFORE appending any system notes
    original_user_message = user_message
    user_message_lower = user_message.lower()

    # ── Auto-detect YouTube URLs ──────────────────────────────────────────
    import re as _re_yt
    yt_pattern = r'(https?://(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)[\w\-]{11}(?:[\?&][^\s]*)?)'
    yt_match = _re_yt.search(yt_pattern, user_message, _re_yt.IGNORECASE)
    if yt_match:
        await summarize_youtube(update, context, yt_match.group(1))
        return
    # ─────────────────────────────────────────────────────────────────────

    # Auto-detect if the user is asking for an image
    # Smart combo detection: any action word + any image word = image request
    image_action_words = ["generate", "create", "make", "draw", "design", "produce", "show", "give", "build", "craft", "paint", "render", "imagine", "visualize"]
    image_subject_words = ["image", "picture", "photo", "pic", "drawing", "illustration", "artwork", "avatar", "logo", "banner", "thumbnail", "wallpaper", "portrait", "poster", "graphic"]
    
    # Exclusion phrases — user is asking ABOUT image generation, not requesting one
    image_exclusion_phrases = [
        "give me a prompt", "give me prompts", "prompt to generate", "prompt for generating",
        "how to generate", "how do i generate", "how can i generate", "how to create",
        "what prompt", "suggest a prompt", "write a prompt", "prompt for image",
        "tips for", "guide for", "help me generate", "ideas for"
    ]
    
    has_action = any(word in user_message_lower.split() for word in image_action_words)
    has_subject = any(word in user_message_lower for word in image_subject_words)
    is_excluded = any(phrase in user_message_lower for phrase in image_exclusion_phrases)
    is_image_request = not is_excluded and ((has_action and has_subject) or "imagine" in user_message_lower or "draw me" in user_message_lower)
    
    if is_image_request:
        user_message += "\n\n[System Note: The image is being generated separately by a dedicated image engine. Your ONLY job right now is to reply with a single short, excited plain-text sentence hyping up what you are about to generate. NO URLs. NO markdown. NO image links. NO code. Just one enthusiastic plain sentence.]"

    await update.message.reply_chat_action("typing")
    
    status_msg = None
    
    # Auto-detect if user is asking for facts/news and needs web context
    web_context = ""
    search_failed = False
    
    needs_search = False
    if not is_image_request:
        needs_search = await check_needs_web_search(original_user_message)
    
    if needs_search:
        # Ask LLM to extract a clean search query
        search_query = original_user_message
        logger.info(f"Auto-RAG triggered for: {search_query}")
        if search_query:
            status_msg = await update.message.reply_text(f"🔍 Searching the web for: '{search_query}'...")
            try:
                tavily_payload = {
                    "api_key": TAVILY_API_KEY,
                    "query": search_query,
                    "search_depth": "basic",
                    "include_answer": False,
                    "max_results": 3
                }
                tavily_resp = await http_client.post("https://api.tavily.com/search", json=tavily_payload, timeout=10.0)
                tavily_resp.raise_for_status()
                data = tavily_resp.json()
                results = data.get('results', [])
                logger.info(f"Tavily returned {len(results)} results")
                if results:
                    web_context = "\n\nReal-time Web Search Context:\n"
                    for r in results:
                        web_context += f"- {r.get('content', '')}\n"
                    await status_msg.edit_text(f"🧠 Analyzing {len(results)} search results...")
                else:
                    search_failed = True
                    await status_msg.edit_text(f"⚠️ No search results found. Answering from memory...")
            except Exception as e:
                logger.error(f"Tavily Error: {e}")
                search_failed = True
                await status_msg.edit_text(f"⚠️ Search failed, answering from memory...")
    
    final_user_message = user_message
    if web_context:
        final_user_message = f"{web_context}\n\nUser Question:\n{user_message}"
    
    # --- Memory Management ---
    if user.id not in chat_histories:
        chat_histories[user.id] = []
        
    chat_histories[user.id].append({"role": "user", "content": final_user_message})
    
    # Keep only the last MAX_HISTORY messages
    if len(chat_histories[user.id]) > MAX_HISTORY:
        chat_histories[user.id] = chat_histories[user.id][-MAX_HISTORY:]
        
    base_system = (
        "You are CogniX, an elite AI assistant built on the Hermes intelligence platform. "
        "You are deployed as a private Telegram bot. "
        "IDENTITY RULES: If anyone asks 'what model are you?', 'who made you?', 'what AI are you?', or any similar identity question, "
        "you MUST respond with something like: 'I am CogniX, a next-generation AI assistant powered by the Hermes intelligence platform.' "
        "NEVER reveal the underlying model names. NEVER use tool_call, function_call, XML tags, or structured output — only plain conversational text. "
        "If real-time web search context is provided, base your answer on it. "
    )
    
    if active_mode == "study":
        base_system += "PERSONA: You are a knowledgeable, patient, and highly structured University Professor. Explain concepts step-by-step, use analogies, encourage critical thinking, and format answers beautifully with markdown headers and bullet points."
    elif active_mode == "coder":
        base_system += "PERSONA: You are a Senior Software Engineer. Zero fluff. No conversational filler or emojis. Output strictly formatted, highly optimized code blocks. Focus on security, performance, and best practices."
    elif active_mode == "creative":
        base_system += "PERSONA: You are an imaginative writer and brainstorming partner. Be highly verbose, creative, and engaging. Use metaphors, avoid strict bullet-point structures, and focus on engaging prose."
    elif active_mode == "concise":
        base_system += "PERSONA: You are a rapid-response AI. Be extremely brief. Answer in 1 to 2 sentences MAXIMUM. Get straight to the point."
    else:
        base_system += "Be sharp, confident, and concise."

    system_prompt = {"role": "system", "content": base_system}
    
    messages = [system_prompt] + chat_histories[user.id]
    # -------------------------

    max_retries = 3
    for attempt in range(max_retries):
        base_url, api_key, extra_headers = get_provider_info(model_to_use)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "HermesTelegramBot/1.0",
            **extra_headers
        }
        
        payload = {
            "model": model_to_use,
            "messages": messages
        }
        
        try:
            response = await http_client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            reply_text = data['choices'][0]['message']['content']
            # Strip ALL known tool_call formats
            import re as _re
            reply_text = _re.sub(r'<tool_call>.*?</tool_call>', '', reply_text, flags=_re.DOTALL)
            reply_text = _re.sub(r'<tool_call>.*?<\|tool_call_argument_end\|>', '', reply_text, flags=_re.DOTALL)
            reply_text = _re.sub(r'<tool_call>.*$', '', reply_text, flags=_re.DOTALL)
            reply_text = _re.sub(r'<\|tool_call_argument_begin\|>.*?<\|tool_call_argument_end\|>', '', reply_text, flags=_re.DOTALL)
            # Strip self-generated markdown image links like ![alt](url)
            reply_text = _re.sub(r'!\[.*?\]\(https?://[^\)]+\)', '', reply_text, flags=_re.DOTALL)
            reply_text = reply_text.strip()
            
            # --- Save Assistant Reply to Memory ---
            chat_histories[user.id].append({"role": "assistant", "content": reply_text})
            # ----------------------------------------
            
            formatted_text = parse_markdown_to_html(reply_text)
            
            # Voice TTS Reply
            if context.user_data.get('wants_voice_reply', False):
                try:
                    await update.message.reply_chat_action("record_voice")
                    spoken_text = _re.sub(r'[*_`~#]', '', reply_text)
                    
                    voice_name = 'en-US-AriaNeural'
                    if any('\u0900' <= c <= '\u097f' for c in spoken_text):
                        voice_name = 'hi-IN-SwaraNeural'
                        
                    communicate = edge_tts.Communicate(spoken_text, voice_name)
                    
                    voice_bytes = b""
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            voice_bytes += chunk["data"]
                            
                    await update.message.reply_voice(voice=voice_bytes)
                    
                    # Clean up search status message if it exists
                    if status_msg and not search_failed:
                        await status_msg.delete()
                        
                except Exception as e:
                    logger.error(f"TTS Error: {e}")
                    # Fallback to text if TTS fails
                    await send_long_message(update, formatted_text, status_msg if not search_failed else None, parse_mode='HTML')
                finally:
                    context.user_data['wants_voice_reply'] = False
            else:
                # Normal Text Reply
                await send_long_message(update, formatted_text, status_msg if not search_failed else None, parse_mode='HTML')
            
            # Fire image generation AFTER the LLM reply is delivered
            # Use original_user_message to keep the prompt clean (no system notes!)
            if is_image_request:
                context.args = original_user_message.split()
                asyncio.create_task(imagine_command(update, context))
            
            return # Success!
            
        except Exception as e:
            logger.error(f"Model {model_to_use} failed: {e}")
            if attempt < max_retries - 1:
                # Rotate to the next model automatically
                model_to_use = get_next_model()
                # Silently retry to avoid confusing the user with scary warning messages
                if status_msg and active_mode == "default":
                    # Only show the retry message if they are in default mode
                    pass
            else:
                err_msg = "An error occurred communicating with all AI models. Please try again later."
                await notify_admin_error(context, "chat_message (All models failed)", e)
                if status_msg:
                    await status_msg.edit_text(err_msg)
                else:
                    await update.message.reply_text(err_msg)

# ==========================================
# Voice Transcription (Whisper) & TTS
# ==========================================
import io
import edge_tts

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not await check_access(update):
        return

    status_msg = await update.message.reply_text("🎙️ Listening...")
    try:
        from config import GROQ_API_KEY
        if not GROQ_API_KEY:
            await status_msg.edit_text("❌ Voice transcription requires a GROQ_API_KEY in the config.")
            return

        file = await context.bot.get_file(update.message.voice.file_id)
        file_bytes = await file.download_as_bytearray()
        
        headers = {'Authorization': f'Bearer {GROQ_API_KEY}'}
        files = {
            'file': ('audio.ogg', io.BytesIO(file_bytes), 'audio/ogg')
        }
        data = {
            'model': 'whisper-large-v3',
            'response_format': 'json'
        }
        
        resp = await http_client.post('https://api.groq.com/openai/v1/audio/transcriptions', headers=headers, files=files, data=data, timeout=30.0)
        resp.raise_for_status()
        transcription = resp.json().get('text', '').strip()
        
        if not transcription:
            await status_msg.edit_text("❌ Couldn't hear anything in that audio.")
            return

        await status_msg.delete()
        
        # Inject the transcribed text directly into the main chat handler!
        # We flag the context so chat_message knows to reply with Voice (TTS)
        context.user_data['wants_voice_reply'] = True
        await chat_message(update, context, voice_text=transcription)
        
    except Exception as e:
        logger.error(f"Voice Transcription Error: {e}")
        await status_msg.edit_text("❌ Failed to transcribe the audio.")

# ==========================================
# Background Tasks & Initialization
# ==========================================
async def check_models_health(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Constantly test every model in background and notify admin on failure/recovery."""
    if not ADMIN_ID:
        return
        
    failed_models = []
    for model in AVAILABLE_MODELS:
        base_url, api_key, extra_headers = get_provider_info(model)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            **extra_headers
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5
        }
        try:
            resp = await http_client.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=10.0)
            resp.raise_for_status()
        except Exception:
            failed_models.append(model)
            
    if failed_models:
        failed_str = ", ".join(failed_models)
        await context.bot.send_message(
            chat_id=ADMIN_ID, 
            text=f"⚠️ **Model Health Alert**\nThe following models are currently unresponsive or failing:\n`{failed_str}`",
            parse_mode='Markdown'
        )

async def post_init(application: Application) -> None:
    """Setup custom command menus and start background tasks."""
    try:
        # 1. Set Command Menus via direct HTTP API for absolute reliability
        url = f'https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands'
        basic_cmds = [
            {'command': 'start', 'description': 'Start interacting with the bot'},
            {'command': 'help', 'description': 'Show help message'},
            {'command': 'search', 'description': 'Search the web for real-time info'},
            {'command': 'imagine', 'description': 'Generate an AI image from a prompt'},
            {'command': 'model', 'description': 'List or switch AI models'},
            {'command': 'mode', 'description': 'Switch between different AI personas and behaviors'}
        ]
        
        try:
            # Set basic commands for everyone in private chats (overrides BotFather legacy commands)
            await http_client.post(url, json={'commands': basic_cmds, 'scope': {'type': 'all_private_chats'}}, timeout=10.0)
            # Also override for group chats
            await http_client.post(url, json={'commands': basic_cmds, 'scope': {'type': 'all_group_chats'}}, timeout=10.0)
            
            if ADMIN_ID:
                admin_cmds = basic_cmds + [
                    {'command': 'adduser', 'description': 'Add a new user (Admin)'},
                    {'command': 'removeuser', 'description': 'Remove a user (Admin)'},
                    {'command': 'users', 'description': 'List all authorized users (Admin)'},
                    {'command': 'broadcast', 'description': 'Send announcement to all users (Admin)'},
                    {'command': 'stats', 'description': 'View bot statistics (Admin)'},
                    {'command': 'logs', 'description': 'View recent system logs (Admin)'},
                    {'command': 'clearhistory', 'description': 'Clear user memory (Admin)'},
                    {'command': 'maintenance', 'description': 'Toggle maintenance mode (Admin)'},
                    {'command': 'ban', 'description': 'Permanently ban a user (Admin)'},
                    {'command': 'unban', 'description': 'Unban a user (Admin)'}
                ]
                # Set admin commands ONLY for the Admin
                await http_client.post(url, json={'commands': admin_cmds, 'scope': {'type': 'chat', 'chat_id': ADMIN_ID}}, timeout=10.0)
        except Exception as e:
            logger.error(f"Failed to set command menus via HTTP: {e}")
            
        if ADMIN_ID:
            # 2. Start Health Check Job (Every 30 minutes)
            application.job_queue.run_repeating(check_models_health, interval=1800, first=10)
            
            # 3. Send Startup Notification
            await application.bot.send_message(
                chat_id=ADMIN_ID, 
                text="🚀 **Deployment Successful!**\nNew AI instance is online and routing traffic.\n\n*Note: Restart your Telegram app if the command menu doesn't update immediately.*", 
                parse_mode='Markdown'
            )
            logger.info("Startup setup complete.")
    except Exception as e:
        logger.error(f"Failed to complete post_init setup: {e}")

def main() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing or empty. Please check your config.py.")
        return

    logger.info("Starting Hermes Bot with VyceAI integration...")
    
    # Start the dummy web server for Render health checks
    try:
        from keep_alive import keep_alive
        keep_alive()
        logger.info("Keep-alive server started.")
    except Exception as e:
        logger.error(f"Failed to start keep-alive server: {e}")

    application = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("imagine", imagine_command))
    application.add_handler(CommandHandler("model", model_command))
    application.add_handler(CommandHandler("mode", mode_command))
    application.add_handler(CommandHandler("adduser", adduser_command))
    application.add_handler(CommandHandler("removeuser", removeuser_command))
    application.add_handler(CommandHandler("users", users_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("logs", logs_command))
    application.add_handler(CommandHandler("clearhistory", clearhistory_command))
    application.add_handler(CommandHandler("maintenance", maintenance_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CallbackQueryHandler(mode_callback, pattern='^mode_'))
    application.add_handler(MessageHandler(filters.Document.ALL, summarize_document))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_message))

    logger.info("Bot is polling for updates...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
