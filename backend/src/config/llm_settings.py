"""LLM provider configuration (Phase 1: Internal unified settings).

Loads LLM configuration from environment variables with validation.
Supports multiple providers: Anthropic, OpenRouter, OpenAI, Google.
"""

from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    GOOGLE = "google"


class LLMSettings(BaseSettings):
    """LLM provider configuration (Phase 1: Internal only).

    Configuration is loaded from environment variables or .env file.
    Use model aliases (e.g., claude-sonnet) instead of dated versions.
    """

    # Provider selection
    DEFAULT_LLM_PROVIDER: LLMProvider = LLMProvider.OPENROUTER

    # API Keys (at least one required based on provider)
    OPENROUTER_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""

    # Model selection (free tier: via OpenRouter)
    DEFAULT_MODEL: str = "openrouter/deepseek/deepseek-v4-flash"

    # OpenRouter metadata (optional, for analytics)
    OR_SITE_URL: str = "https://github.com/yourusername/the-lantern"
    OR_APP_NAME: str = "HP Investigation Game"

    # Fallback configuration
    ENABLE_FALLBACK: bool = True
    FALLBACK_MODEL: str = "openrouter/google/gemma-4-31b-it"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def get_api_key_for_provider(self, provider: LLMProvider | None = None) -> str:
        """Get API key for specified provider.

        Args:
            provider: Provider to get key for. Defaults to DEFAULT_LLM_PROVIDER.

        Returns:
            API key string (may be empty if not configured)
        """
        target = provider or self.DEFAULT_LLM_PROVIDER
        key_map = {
            LLMProvider.OPENROUTER: self.OPENROUTER_API_KEY,
            LLMProvider.ANTHROPIC: self.ANTHROPIC_API_KEY,
            LLMProvider.OPENAI: self.OPENAI_API_KEY,
            LLMProvider.GOOGLE: self.GOOGLE_API_KEY,
        }
        return key_map.get(target, "")

    def validate_keys(self) -> None:
        """Validate that required API keys are present.

        Raises:
            ValueError: If API key for configured provider is missing
        """
        key = self.get_api_key_for_provider(self.DEFAULT_LLM_PROVIDER)
        if not key:
            provider_name = self.DEFAULT_LLM_PROVIDER.value.upper()
            raise ValueError(
                f"Missing API key for provider: {self.DEFAULT_LLM_PROVIDER.value}. "
                f"Set {provider_name}_API_KEY in .env"
            )


# Singleton instance (cached for performance)
_settings: LLMSettings | None = None


def get_llm_settings() -> LLMSettings:
    """Get singleton LLM settings instance.

    Validates API keys on first access. Uses module-level caching
    for performance in multi-request scenarios.

    Returns:
        Configured LLMSettings instance

    Raises:
        ValueError: If required API key is missing
    """
    global _settings
    if _settings is None:
        _settings = LLMSettings()
        _settings.validate_keys()
    return _settings


