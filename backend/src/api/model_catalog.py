"""Dynamic LLM model catalog fetched from OpenRouter API.

Fetches available models from OpenRouter, caches in memory, refreshes daily.
Groups by provider and returns top N most recent text models per provider.

For direct providers (anthropic, openai, google): top 5 most recent.
For openrouter: top 10 most recent, excluding models from direct providers.
"""

import asyncio
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Cache state
_cache: list[dict[str, Any]] = []
_cache_time: float = 0
_CACHE_TTL = 86400  # 24 hours
_refresh_lock: asyncio.Lock | None = None

# Providers that have direct API access (BYOK)
DIRECT_PROVIDERS = {"anthropic", "openai", "google"}

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/models"


async def _fetch_openrouter_models() -> list[dict[str, Any]]:
    """Fetch model list from OpenRouter API."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(OPENROUTER_API_URL)
        resp.raise_for_status()
        body: dict[str, Any] = resp.json()
        models: list[dict[str, Any]] = body.get("data", [])
        return models


def _is_chat_model(model: dict[str, Any]) -> bool:
    """Check if model is a text chat model (excludes audio/image generators)."""
    output_modalities = set(model.get("architecture", {}).get("output_modalities", []))
    # Must output text, must NOT output audio or image
    return "text" in output_modalities and not output_modalities.intersection({"audio", "image"})


def _parse_model(model: dict[str, Any], provider_override: str | None = None) -> dict[str, str | bool]:
    """Parse an OpenRouter model into our ModelInfo format."""
    model_id = model["id"]
    name = model.get("name", model_id)

    # Strip "Provider: " prefix from name (e.g. "Anthropic: Claude Sonnet 4" -> "Claude Sonnet 4")
    if ": " in name:
        name = name.split(": ", 1)[1]

    # Detect free models
    is_free = ":free" in model_id
    pricing = model.get("pricing", {})
    prompt_cost = float(pricing.get("prompt", 0))
    if prompt_cost == 0 and not is_free:
        is_free = True

    # For direct providers, the model ID from OpenRouter works with LiteLLM as-is
    # (e.g. "anthropic/claude-sonnet-4" is valid for LiteLLM with an Anthropic key)
    provider = provider_override or model_id.split("/")[0]

    # Remap model IDs for LiteLLM compatibility:
    # - Google: LiteLLM expects "gemini/" prefix, OpenRouter uses "google/"
    # - OpenRouter-exclusive: need "openrouter/" prefix for LiteLLM routing
    litellm_id = model_id
    if provider == "google" and model_id.startswith("google/"):
        litellm_id = "gemini/" + model_id.split("/", 1)[1]
    elif provider_override == "openrouter" and not model_id.startswith("openrouter/"):
        litellm_id = "openrouter/" + model_id

    return {
        "id": litellm_id,
        "name": name,
        "provider": provider,
        "free": is_free,
    }


def _curate_models(raw_models: list[dict[str, Any]]) -> list[dict[str, str | bool]]:
    """Curate models: top 5 per direct provider, top 10 OpenRouter-exclusive."""
    # Filter to text models only
    text_models = [m for m in raw_models if _is_chat_model(m)]

    # Sort by created date descending (most recent first)
    text_models.sort(key=lambda x: x.get("created", 0), reverse=True)

    result: list[dict[str, str | bool]] = []

    # Direct providers: top 5 each, skip :free duplicates
    for provider in DIRECT_PROVIDERS:
        provider_models = [
            m for m in text_models
            if m["id"].split("/")[0] == provider and ":free" not in m["id"]
        ]
        for m in provider_models[:5]:
            result.append(_parse_model(m))

    # OpenRouter-exclusive: top 10, excluding direct providers
    exclusive = [
        m for m in text_models
        if m["id"].split("/")[0] not in DIRECT_PROVIDERS and ":free" not in m["id"]
    ]
    for m in exclusive[:10]:
        result.append(_parse_model(m, provider_override="openrouter"))

    return result


async def get_cached_models() -> list[dict[str, str | bool]]:
    """Get curated model list, fetching from OpenRouter if cache is stale."""
    global _cache, _cache_time, _refresh_lock

    if _cache and (time.time() - _cache_time) < _CACHE_TTL:
        return _cache

    if _refresh_lock is None:
        _refresh_lock = asyncio.Lock()

    async with _refresh_lock:
        if _cache and (time.time() - _cache_time) < _CACHE_TTL:
            return _cache

        try:
            raw = await _fetch_openrouter_models()
            _cache = _curate_models(raw)
            _cache_time = time.time()
            logger.info("Model catalog refreshed: %d models cached", len(_cache))
        except Exception:
            logger.warning("Failed to fetch OpenRouter models, using cache", exc_info=True)
            if not _cache:
                return []

    return _cache
