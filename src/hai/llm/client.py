from __future__ import annotations

from openai import OpenAI

from hai.config import Settings, get_settings
from hai.llm.prompts import SYSTEM_PROMPT, user_prompt
from hai.llm.schemas import Classification


class LLMError(Exception):
    pass


def _client(settings: Settings) -> tuple[OpenAI, str]:
    if settings.llm_provider == "openrouter":
        if not settings.openrouter_api_key:
            raise LLMError("OPENROUTER_API_KEY is not set")
        return (
            OpenAI(
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url,
            ),
            settings.openrouter_model,
        )
    if not settings.xai_api_key:
        raise LLMError("XAI_API_KEY is not set")
    return (
        OpenAI(api_key=settings.xai_api_key, base_url=settings.xai_base_url),
        settings.xai_model,
    )


def classify_with_model(
    *,
    title: str,
    url: str,
    source_name: str,
    source_authority: float,
    published_at: str | None,
    text: str,
    source_categories: list[str],
    settings: Settings | None = None,
) -> Classification:
    settings = settings or get_settings()
    client, model = _client(settings)
    prompt = user_prompt(
        title=title,
        url=url,
        source_name=source_name,
        source_authority=source_authority,
        published_at=published_at,
        text=text,
        source_categories=source_categories,
    )
    try:
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format=Classification,
        )
    except Exception as exc:  # noqa: BLE001 - surface any provider failure
        raise LLMError(str(exc)) from exc
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raw = completion.choices[0].message.content or ""
        try:
            return Classification.model_validate_json(raw)
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Model returned unparsable classification: {exc}") from exc
    return parsed
