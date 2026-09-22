# config.py
import itertools
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
_guest_ids_raw = os.environ.get("GUEST_IDS", "")
GUEST_IDS = [int(gid.strip()) for gid in _guest_ids_raw.split(",") if gid.strip().isdigit()]
GITHUB_PAT = os.environ.get("GITHUB_PAT", "")

# ==================================
# API Credentials
# ==================================
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

# Poolside AI — Round-robin across multiple keys (direct API)
POOLSIDE_API_KEYS = [
    os.environ.get("POOLSIDE_API_KEY_1", ""),
    os.environ.get("POOLSIDE_API_KEY_2", "")
]
POOLSIDE_API_KEYS = [k for k in POOLSIDE_API_KEYS if k]
poolside_key_iterator = itertools.cycle(POOLSIDE_API_KEYS) if POOLSIDE_API_KEYS else None

def get_poolside_key():
    return next(poolside_key_iterator) if poolside_key_iterator else ""

# OpenRouter — single key, routes to many free models
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# Groq — ultra-fast inference (activate key on console.groq.com first)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# ==================================
# Model Routing Registry
# Only VERIFIED ALIVE models are listed here.
# ==================================
MODELS = {
    # --- Poolside AI (Direct, Round-Robin Keys) ---
    "poolside/laguna-s-2.1": {
        "url": "https://inference.poolside.ai/v1",
        "key_func": get_poolside_key
    },
    "poolside/laguna-xs-2.1": {
        "url": "https://inference.poolside.ai/v1",
        "key_func": get_poolside_key
    },

    # --- OpenRouter Free Models ---
    "nvidia/nemotron-3-super-120b-a12b:free": {
        "url": "https://openrouter.ai/api/v1",
        "key": OPENROUTER_API_KEY,
        "extra_headers": {
            "HTTP-Referer": "https://hermes-bot.onrender.com",
            "X-Title": "Hermes Telegram Bot"
        }
    },
    "qwen/qwen3.8-27b:free": {
        "url": "https://openrouter.ai/api/v1",
        "key": OPENROUTER_API_KEY,
        "extra_headers": {
            "HTTP-Referer": "https://hermes-bot.onrender.com",
            "X-Title": "Hermes Telegram Bot"
        }
    },

    # --- Groq (Ultra-fast — activate key at console.groq.com) ---
    "llama3-70b-8192": {
        "url": "https://api.groq.com/openai/v1",
        "key": GROQ_API_KEY
    },
}

AVAILABLE_MODELS = list(MODELS.keys())
DEFAULT_MODEL = "auto"  # 'auto' triggers round-robin

model_iterator = itertools.cycle(AVAILABLE_MODELS)

def get_next_model():
    """Returns the next model in the round-robin cycle."""
    return next(model_iterator)

def get_provider_info(model_name):
    """Returns the (base_url, api_key, extra_headers) for the requested model."""
    info = MODELS.get(model_name, list(MODELS.values())[0])
    key = info["key_func"]() if "key_func" in info else info.get("key", "")
    extra_headers = info.get("extra_headers", {})
    return info["url"], key, extra_headers
