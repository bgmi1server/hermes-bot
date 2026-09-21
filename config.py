# config.py
import itertools
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
GUEST_IDS = []  # List of guest IDs

# ==================================
# API Credentials
# ==================================
VYCE_API_KEYS = [
    os.environ.get("VYCE_API_KEY_1", ""),
    os.environ.get("VYCE_API_KEY_2", "")
]
VYCE_API_KEYS = [k for k in VYCE_API_KEYS if k] # Filter empty
key_iterator = itertools.cycle(VYCE_API_KEYS) if VYCE_API_KEYS else None

def get_vyce_key():
    return next(key_iterator) if key_iterator else ""

HCNSEC_API_KEY = os.environ.get("HCNSEC_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

# ==================================
# Model Routing Registry
# ==================================
MODELS = {
    # VyceAI Models (Uses round-robin keys)
    "claude-sonnet-4-6": {"url": "https://vyceai.com/v1", "key_func": get_vyce_key},
    "agnes-3.0-flash": {"url": "https://vyceai.com/v1", "key_func": get_vyce_key},
    
    # HCNSec Models (Verified Active)
    "DeepSeek-V4.1-Flash": {"url": "https://api.hcnsec.cn/v1", "key": HCNSEC_API_KEY},
    "kimi-k3": {"url": "https://api.hcnsec.cn/v1", "key": HCNSEC_API_KEY},
    "step-3.7-flash": {"url": "https://api.hcnsec.cn/v1", "key": HCNSEC_API_KEY},
    "Qwen3.8-27B": {"url": "https://api.hcnsec.cn/v1", "key": HCNSEC_API_KEY}
}

AVAILABLE_MODELS = list(MODELS.keys())
DEFAULT_MODEL = "auto"  # 'auto' triggers round-robin

model_iterator = itertools.cycle(AVAILABLE_MODELS)

def get_next_model():
    """Returns the next model in the round-robin cycle."""
    return next(model_iterator)

def get_provider_info(model_name):
    """Returns the (base_url, api_key) for the requested model."""
    info = MODELS[model_name]
    if "key_func" in info:
        return info["url"], info["key_func"]()
    return info["url"], info["key"]

def get_image_provider_info():
    """Returns the credentials specifically for grok-imagine-2."""
    return "https://vyceai.com/v1", get_vyce_key()
