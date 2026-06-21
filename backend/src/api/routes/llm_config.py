"""LLM configuration endpoints: API key verification, model listing."""

from fastapi import APIRouter, Request

from src.api.llm_client import UnsupportedModelError, validate_byok_model
from src.api.rate_limit import VERIFY_KEY_RATE, limiter
from src.api.schemas import ModelInfo, VerifyKeyRequest, VerifyKeyResponse
from src.config.llm_settings import get_llm_settings

router = APIRouter()

_VERIFY_MODELS: dict[str, str] = {
    "openrouter": "openrouter/google/gemini-2.0-flash-001",
    "anthropic": "anthropic/claude-haiku-4-5",
    "openai": "openai/gpt-4o-mini",
    "google": "gemini/gemini-2.0-flash",
}


@router.post("/llm/verify", response_model=VerifyKeyResponse)
@limiter.limit(VERIFY_KEY_RATE)
async def verify_api_key(request: Request, body: VerifyKeyRequest) -> VerifyKeyResponse:
    """Verify a user's API key with a minimal test call."""
    test_model = body.model or _VERIFY_MODELS.get(body.provider)
    if not test_model:
        return VerifyKeyResponse(valid=False, error=f"Unknown provider: {body.provider}")

    if body.model:
        try:
            validate_byok_model(body.model)
        except UnsupportedModelError as e:
            return VerifyKeyResponse(valid=False, error=str(e))

    try:
        from litellm import acompletion
        from litellm.exceptions import AuthenticationError, RateLimitError

        await acompletion(
            model=test_model,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=5,
            api_key=body.api_key,
        )
        return VerifyKeyResponse(valid=True)
    except AuthenticationError:
        return VerifyKeyResponse(valid=False, error="Invalid API key")
    except RateLimitError:
        return VerifyKeyResponse(valid=False, error="Rate limited — try again shortly")
    except Exception:
        return VerifyKeyResponse(valid=False, error="Verification failed — check key and provider")


@router.get("/llm/active")
async def get_active_model() -> dict[str, str]:
    """Return the currently active free-tier model name."""
    settings = get_llm_settings()
    model_id = settings.DEFAULT_MODEL
    # Extract human-readable name from model ID (last segment, cleaned up)
    name = model_id.rsplit("/", 1)[-1].replace(":free", "").replace("-", " ").title()
    return {"model_id": model_id, "model_name": name}


@router.get("/llm/models")
async def get_available_models() -> list[ModelInfo]:
    """Return curated models fetched from OpenRouter API (cached daily).

    Direct providers (anthropic, openai, google): top 5 most recent text models.
    OpenRouter: top 10 most recent text models exclusive to OpenRouter.
    """
    from src.api.model_catalog import get_cached_models

    models = await get_cached_models()
    return [
        ModelInfo(
            id=str(m["id"]),
            name=str(m["name"]),
            provider=str(m["provider"]),
            free=bool(m.get("free", False)),
        )
        for m in models
    ]
