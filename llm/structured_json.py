from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel

TModel = TypeVar("TModel", bound=BaseModel)


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if not text.startswith("```"):
        return text

    lines = text.split("\n")
    if len(lines) >= 3:
        return "\n".join(lines[1:-1]).strip()

    return text.strip("`").strip()


async def ainvoke_json(llm_client: Any, prompt: str) -> dict:
    """Invoke an async LangChain-compatible client and parse JSON response."""
    response = await llm_client.ainvoke(prompt)
    response_text = response.content if hasattr(response, "content") else str(response)
    response_text = _strip_code_fences(response_text)
    return json.loads(response_text)


async def ainvoke_pydantic(llm_client: Any, prompt: str, model: type[TModel]) -> TModel:
    """Invoke LLM and parse/validate JSON into a Pydantic model."""
    data = await ainvoke_json(llm_client, prompt)

    # Drop explicit nulls so model defaults can apply.
    for key, value in list(data.items()):
        if value is None:
            del data[key]

    return model(**data)
