from __future__ import annotations

from config.settings import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_PROVIDER,
    OPENROUTER_APP_NAME,
    OPENROUTER_HTTP_REFERER,
)


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
        default_headers: dict[str, str] = {}
        if OPENROUTER_HTTP_REFERER:
            default_headers["HTTP-Referer"] = OPENROUTER_HTTP_REFERER
        if OPENROUTER_APP_NAME:
            default_headers["X-Title"] = OPENROUTER_APP_NAME
        if default_headers:
            kwargs["default_headers"] = default_headers

    return ChatOpenAI(**kwargs)
