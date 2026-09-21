import logging
import httpx
import asyncio
import time
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
try:
    from config import (
        BOT_TOKEN, ADMIN_ID, GUEST_IDS,
        get_provider_info, get_image_provider_info, get_next_model,
        AVAILABLE_MODELS, DEFAULT_MODEL, TAVILY_API_KEY
    )
except ImportError:
    raise ImportError("Please create a config.py file with necessary configurations.")

# ==========================================
# Logging Configuration
# ==========================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

current_model = DEFAULT_MODEL

# Global HTTP client for connection pooling (speeds up requests)
http_client = httpx.AsyncClient(timeout=120.0)

# ==========================================
# Role-Based Access Control (RBAC)
# ==========================================
def is_authorized(user_id: int) -> bool:
    return user_id == ADMIN_ID or user_id in GUEST_IDS

# ==========================================
# Command Handlers
# ==========================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_authorized(user.id):
        await update.message.reply_text("Unauthorized access. You cannot use this bot.")
        return

    welcome_msg = (
        f"Hello {user.first_name}! I am Hermes, your AI assistant.\n\n"
        f"Currently using model: {current_model}\n\n"
        "You can chat with me directly, use /search to find information, or use /imagine to generate images!"
    )
    await update.message.reply_text(welcome_msg)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_authorized(user.id):
        await update.message.reply_text("Unauthorized access.")
        return

    help_msg = (
        "Available Commands:\n"
        "/start - Start interacting with the bot\n"
        "/help - Show this help message\n"
        "/search <query> - Search DuckDuckGo for the given query\n"
        "/imagine <prompt> - Generate an image using Grok\n"
        "/model - List available models or switch model (/model <name>)\n\n"
        f"Current model: {current_model}\n"
        "Just type any message to chat!"
    )
    await update.message.reply_text(help_msg)

async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global current_model
    user = update.effective_user
    if not is_authorized(user.id):
        return

    if not context.args:
        models_str = "\n".join([f"- {m}" for m in AVAILABLE_MODELS])
        await update.message.reply_text(
            f"Currently using: {current_model}\n\nAvailable models:\n- auto (Round-robin across all)\n{models_str}\n\n"
            "To switch, use: /model <model_name> or /model auto"
        )
        return

    requested_model = context.args[0]
    if requested_model == "auto" or requested_model in AVAILABLE_MODELS:
        current_model = requested_model
        await update.message.reply_text(f"Successfully switched to model: {current_model}")
    else:
        await update.message.reply_text(f"Invalid model. Please choose 'auto' or from the available models.")

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_authorized(user.id):
        return

    query = " ".join(context.args) if context.args else None
    
    if not query:
        await update.message.reply_text("Please provide a search query. Usage: /search <your query>")
        return

    await update.message.reply_chat_action("typing")
    
    try:
        results = []
        with DDGS() as ddgs:
            search_results = ddgs.text(query, max_results=3)
            for result in search_results:
                title = result.get('title', 'No Title')
                href = result.get('href', 'No URL')
                body = result.get('body', 'No snippet available.')
                results.append(f"🔹 {title}\n🔗 {href}\n📝 {body}")
        
        if results:
            response_text = f"Search results for '{query}':\n\n" + "\n\n".join(results)
            await update.message.reply_text(response_text)
        else:
            await update.message.reply_text("No results found for your query.")
            
    except Exception as e:
        logger.error(f"Error during DuckDuckGo search: {e}")
        await update.message.reply_text("An error occurred while searching. Please try again later.")


async def imagine_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_authorized(user.id):
        return

    prompt = " ".join(context.args) if context.args else None
    
    if not prompt:
        await update.message.reply_text("Please provide a prompt. Usage: /imagine <your prompt>")
        return

    status_msg = await update.message.reply_text(f"✨ Enhancing your prompt with AI...")
    
    # --- Step 1: AI Prompt Enhancement ---
    model_to_use = get_next_model() if current_model == "auto" else current_model
    base_url, api_key = get_provider_info(model_to_use)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "HermesTelegramBot/1.0"
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
        response = await http_client.get(image_url, timeout=120.0)
        response.raise_for_status()
        
        timer_task.cancel()
        elapsed_total = int(time.time() - start_time)
            
    except Exception as e:
        timer_task.cancel()
        logger.error(f"Error generating image: {e}")
        await status_msg.edit_text("An error occurred while generating the image. Please try again later.")
        return

    try:
        # Send the photo back to Telegram with the prompt as the caption
        caption_text = f"Prompt: {prompt}"
        if len(caption_text) > 1000:
            caption_text = caption_text[:1000] + "..."
        await update.message.reply_photo(photo=image_url, caption=caption_text)
        
        footer = f"✅ Image generated in {elapsed_total} seconds!"
        await status_msg.edit_text(footer)
    except Exception as e:
        logger.error(f"Error sending photo to Telegram: {e}")
        try:
            await status_msg.edit_text(f"✅ Image generated in {elapsed_total} seconds! (Network took too long to deliver it)")
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
# Message Handler (Chatting with LLM)
# ==========================================
chat_histories = {}
MAX_HISTORY = 10
async def chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_authorized(user.id):
        return

    user_message = update.message.text
    if not user_message:
        return
        
    model_to_use = get_next_model() if current_model == "auto" else current_model
        
    # Check if this is a reply to a generated image (Image modification request)
    if update.message.reply_to_message and update.message.reply_to_message.photo:
        old_caption = update.message.reply_to_message.caption
        if old_caption and old_caption.startswith("Prompt: "):
            original_prompt = old_caption[8:]
            
            status_msg = await update.message.reply_text("🧠 Merging prompts...")
            base_url, api_key = get_provider_info(model_to_use)
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
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

    user_message_lower = user_message.lower()
    
    # Auto-detect if the user is asking for an image
    image_triggers = [
        "generate an image", "create an image", "draw a", "draw me", 
        "make a picture", "show me a picture", "generate a picture", 
        "create a picture", "generate image", "imagine",
        "give me an image", "give me a picture", "give me a photo",
        "can you draw", "can you generate", "picture of a", "image of a",
        "photo of a"
    ]
    if any(trigger in user_message_lower for trigger in image_triggers):
        context.args = user_message.split()
        asyncio.create_task(imagine_command(update, context))
        user_message += "\n\n[System Note: The system has already started generating the requested image in the background. DO NOT apologize for not being able to generate images. If the user asked an additional question, answer it now. If they only asked for an image, just enthusiastically say you are generating it!]"

    await update.message.reply_chat_action("typing")
    
    status_msg = None
    
    # Auto-detect if user is asking for facts/news and needs web context
    search_triggers = ["latest news", "news about", "today", "search for", "look up", "current events", "latest updates"]
    web_context = ""
    search_failed = False
    
    # Smart heuristics to avoid searching for math, short words, or basic greetings
    is_math = bool(re.fullmatch(r'^[0-9\s\+\-\*\/\(\)\=\.a-zA-Z]+\??$', user_message)) and len(user_message.split()) <= 4
    ignore_phrases = ["how are you", "who are you", "what are you", "hello", "hi", "thanks", "thank you", "good morning", "goodnight", "bye"]
    is_greeting = any(phrase == user_message_lower.strip('?.,! ') for phrase in ignore_phrases)
    
    needs_search = not is_math and not is_greeting and any(trigger in user_message_lower for trigger in search_triggers)
    
    if needs_search:
        search_query = re.sub(r'^(what do you say about|what do you know about|what do you think about|do you know about|can you tell me about|tell me about|what is|who is|what\'s|search for|look up|latest|news|today)\s+', '', user_message_lower).strip('?.,!')
        if not search_query:
            search_query = user_message.strip('?.,!')
        logger.info(f"Auto-RAG triggered. Cleaned query: {search_query}")
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
        
    system_prompt = {"role": "system", "content": "You are a helpful AI assistant. If real-time web search context is provided, you MUST base your answer entirely on it, even if it contradicts your internal knowledge. Trust the search context as absolute truth."}
    
    messages = [system_prompt] + chat_histories[user.id]
    # -------------------------

    max_retries = 3
    for attempt in range(max_retries):
        base_url, api_key = get_provider_info(model_to_use)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "HermesTelegramBot/1.0"
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
            
            # --- Save Assistant Reply to Memory ---
            chat_histories[user.id].append({"role": "assistant", "content": reply_text})
            # ----------------------------------------
            
            formatted_text = parse_markdown_to_html(reply_text)
            
            if status_msg and not search_failed:
                try:
                    await status_msg.edit_text(formatted_text, parse_mode='HTML')
                except Exception:
                    await status_msg.edit_text(reply_text) # Fallback if HTML fails
            else:
                try:
                    await update.message.reply_text(formatted_text, parse_mode='HTML')
                except Exception:
                    await update.message.reply_text(reply_text)
            return # Success!
            
        except Exception as e:
            logger.error(f"Model {model_to_use} failed: {e}")
            if attempt < max_retries - 1:
                # Rotate to the next model automatically
                model_to_use = get_next_model()
                if status_msg:
                    await status_msg.edit_text(f"⚠️ Model failed, auto-retrying with {model_to_use}...")
                else:
                    status_msg = await update.message.reply_text(f"⚠️ Model failed, auto-retrying with {model_to_use}...")
            else:
                err_msg = "An error occurred communicating with all AI models. Please try again later."
                if status_msg:
                    await status_msg.edit_text(err_msg)
                else:
                    await update.message.reply_text(err_msg)

# ==========================================
# Main Application Entry Point
# ==========================================
async def post_init(application: Application) -> None:
    """Send a notification to the admin when the bot starts up."""
    try:
        if ADMIN_ID:
            await application.bot.send_message(chat_id=ADMIN_ID, text="🚀 **Deployment Successful!** New AI instance is online and routing traffic.", parse_mode='Markdown')
            logger.info("Startup notification sent to Admin.")
    except Exception as e:
        logger.error(f"Failed to send startup notification: {e}")

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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_message))

    logger.info("Bot is polling for updates...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
