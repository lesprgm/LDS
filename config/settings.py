import os
from dotenv import load_dotenv

load_dotenv()

# LLM config only (public-safe)
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter")  # openrouter | openai | anthropic
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
