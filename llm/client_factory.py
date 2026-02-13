"""LangChain client creation (provider-agnostic)."""

from __future__ import annotations

from config.settings import LLM_API_KEY, LLM_MODEL, LLM_PROVIDER, LLM_BASE_URL


def get_llm_client():
    """Create an LLM client from environment-backed settings.

    Supports: openrouter (OpenAI-compatible), openai, anthropic.
    """
    if LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=LLM_MODEL, api_key=LLM_API_KEY, temperature=0)

    from langchain_openai import ChatOpenAI

    kwargs: dict = {
        "model": LLM_MODEL,
        "api_key": LLM_API_KEY,
        "temperature": 0,
    }

    if LLM_PROVIDER == "openrouter":
        kwargs["base_url"] = LLM_BASE_URL
        kwargs["default_headers"] = {
            "HTTP-Referer": "https://foundmoney.ai",
            "X-Title": "FoundMoney.ai",
        }

    return ChatOpenAI(**kwargs)
