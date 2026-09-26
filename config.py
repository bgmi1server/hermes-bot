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

# SeekAI — Round-robin across multiple keys for free text chat models
SEEKAI_API_KEYS = [
    "sk-M6Yy22PAuPRb5bEwJpatK3H1W2GaikZ2zkNFoZdCdP3h4Jwp",
    "sk-lwPVU0Fg2Pf3GzSDDTxD7E9MFSdnNRs3izxkmHUsAoErCWx1",
    "sk-q4dUt9wzrI3uKnVPZSWkY5GZbTvtVGRZJiFpyGkNu4Wq7aaV",
    "sk-znhyN1KTWCytg9Zng3kupLrmUa9ls9nPfamy0IQIfrWY05Tk",
    "sk-qkPC0UYCvma0y2SXaDOA2zxSeaNXsOSgMhixOlVzCOjDtFlj",
    "sk-IHqM3amdBXRsiZteWASJXFKV2J6mWjlDqW9ZX71yVjjtvMpn"
]
seekai_key_iterator = itertools.cycle(SEEKAI_API_KEYS)

def get_seekai_key():
    return next(seekai_key_iterator)

# Conduit — Round-robin across multiple keys for Claude CLI
CONDUIT_API_KEYS = [
    "sk-cdt-eyJpZCI6IjE4NjQ4MTEwOTciLCJ1IjoiIiwibiI6ImRlZmF1bHQiLCJqIjoiZGVmYXVsdCIsImsiOiJhcGkifQ.8omON19NcZSVPa13v_8z6Ymj2qvItnXPlXs0Eod6OJE",
    "sk-cdt-eyJpZCI6Ijg1NTU0MjkyMjIiLCJ1IjoiIiwibiI6ImRlZmF1bHQiLCJqIjoiZGVmYXVsdCIsImsiOiJhcGkifQ.hb5pY1WsMS2aW-8vvYkHIEFud-gzd4LSZ3ZgUkUtbZA"
]
conduit_key_iterator = itertools.cycle(CONDUIT_API_KEYS)

def get_conduit_key():
    return next(conduit_key_iterator)

# OpenRouter — single key, routes to many free models
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# Groq — ultra-fast inference (activate key on console.groq.com first)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# Anthropic / Custom Provider — required for Claude Code CLI autonomous agent
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "")

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
#     "nvidia/nemotron-3-super-120b-a12b:free": {
#         "url": "https://openrouter.ai/api/v1",
#         "key": OPENROUTER_API_KEY,
#         "extra_headers": {
#             "HTTP-Referer": "https://hermes-bot.onrender.com",
#             "X-Title": "Hermes Telegram Bot"
#         }
#     },

    # --- Groq (Ultra-fast — activate key at console.groq.com) ---
    "qwen/qwen3.8-27b": {
        "url": "https://api.groq.com/openai/v1",
        "key": GROQ_API_KEY
    },
    # --- Custom Proxy Free Models (Based on User's API constraints) ---
#     "qwen3.8-27b-free": {
#         "url": "https://openrouter.ai/api/v1",
#         "key": OPENROUTER_API_KEY
#     },
#     "glm-5.3-flash-free": {
#         "url": "https://openrouter.ai/api/v1",
#         "key": OPENROUTER_API_KEY
#     },
    
    # --- SeekAI Free Models (Text Chat Only) ---
#     "seekai/glm-5.3-flash": {
#         "url": "https://seekai.cc/v1",
#         "key_func": get_seekai_key
#     },
#     "seekai/deepseek-v4.1-flash": {
#         "url": "https://seekai.cc/v1",
#         "key_func": get_seekai_key
#     },
    
    # --- Conduit (Claude Proxy) ---
#     "claude-sonnet-4.6": {
#         "url": "https://conduit.ozdoev.net/v1",
#         "key_func": get_conduit_key,
#         "extra_headers": {"anthropic-version": "2023-06-01"},
#         "cli_only": True
#     },
    
    # --- VyceAI (Claude Proxy) ---
    "claude-sonnet-4-6": {
        "url": "https://vyceai.com/v1",
        "key": "sk-ebadd39789735ec25072b720470d5b360aae371a231352d7",
        "extra_headers": {"anthropic-version": "2023-06-01"},
        "cli_only": True
    }
}

# ALL models for health checking
ALL_MODELS = list(MODELS.keys())
HEALTHY_MODELS = ALL_MODELS.copy()

# Filtered lists
AVAILABLE_MODELS = [m for m, info in MODELS.items() if not info.get("cli_only")]
CLAUDE_CLI_MODELS = [m for m, info in MODELS.items() if info.get("cli_only")]

DEFAULT_MODEL = "auto"

chat_model_iterator = itertools.cycle(AVAILABLE_MODELS)
claude_model_iterator = itertools.cycle(CLAUDE_CLI_MODELS) if CLAUDE_CLI_MODELS else itertools.cycle(AVAILABLE_MODELS)

def get_next_model():
    """Returns the next HEALTHY standard chat model in the round-robin cycle."""
    global chat_model_iterator
    pool = HEALTHY_MODELS if HEALTHY_MODELS else AVAILABLE_MODELS
    
    for _ in range(len(AVAILABLE_MODELS)):
        candidate = next(chat_model_iterator)
        if candidate in pool and not MODELS[candidate].get("cli_only"):
            return candidate
            
    return next(chat_model_iterator)

def get_primary_claude_model():
    """Returns the highest priority HEALTHY Claude model (e.g. Conduit)."""
    pool = HEALTHY_MODELS if HEALTHY_MODELS else CLAUDE_CLI_MODELS
    for m in CLAUDE_CLI_MODELS:
        if m in pool:
            return m
    return CLAUDE_CLI_MODELS[0] if CLAUDE_CLI_MODELS else None

def get_next_claude_model():
    """Returns the next HEALTHY Claude-specific model for the CLI fallback."""
    global claude_model_iterator
    pool = HEALTHY_MODELS if HEALTHY_MODELS else CLAUDE_CLI_MODELS
    
    for _ in range(len(CLAUDE_CLI_MODELS)):
        candidate = next(claude_model_iterator)
        if candidate in pool:
            return candidate
            
    return next(claude_model_iterator)

def get_provider_info(model_name):
    """Returns the (base_url, api_key, extra_headers) for the requested model."""
    info = MODELS.get(model_name, list(MODELS.values())[0])
    key = info["key_func"]() if "key_func" in info else info.get("key", "")
    extra_headers = info.get("extra_headers", {})
    return info["url"], key, extra_headers
