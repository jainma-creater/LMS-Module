from functools import lru_cache

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment / .env.

    Secrets are never committed; see .env.example for placeholder names.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    app_name: str = Field(default="ai-lms", alias="APP_NAME")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_url: str = Field(
        default="postgresql+psycopg://lms:lms@localhost:5432/lms",
        alias="DATABASE_URL",
    )

    # Reserved for later phases; unused until configured and approved.
    redis_url: str | None = Field(default=None, alias="REDIS_URL")

    # Authentication. 'disabled' (default, deny-by-default) is the safe setting.
    # 'development' is a TEMPORARY local-only access mode: it is refused unless
    # APP_ENV=development. See docs/SECURITY.md and docs/adr/ADR-002-identity-provider.md.
    auth_provider: str = Field(default="disabled", alias="AUTH_PROVIDER")
    # Roles granted to the local development identity (AUTH_PROVIDER=development
    # only). Comma-separated canonical role names. system_admin is never allowed.
    dev_access_roles: str = Field(default="learning_admin", alias="DEV_ACCESS_ROLES")
    oidc_issuer_url: HttpUrl | None = Field(default=None, alias="OIDC_ISSUER_URL")
    oidc_client_id: str | None = Field(default=None, alias="OIDC_CLIENT_ID")
    oidc_client_secret: str | None = Field(default=None, alias="OIDC_CLIENT_SECRET")

    # AI Training Studio & Content Generation
    ai_provider: str = Field(default="gemini", alias="AI_PROVIDER")
    ai_model: str = Field(default="gemini-1.5-flash", alias="AI_MODEL")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")

    # Local AI & Media Tooling
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    embedding_model: str = Field(default="nomic-embed-text", alias="EMBEDDING_MODEL")
    piper_binary_path: str = Field(default="piper", alias="PIPER_BINARY_PATH")
    gemini_tts_model: str = Field(default="gemini-3.8-flash-tts", alias="GEMINI_TTS_MODEL")
    # Renderer service (Remotion) used to produce course videos.
    renderer_url: str = Field(default="http://127.0.0.1:8090", alias="RENDERER_URL")
    # Public origin of the web app; used to build absolute media links for lessons.
    public_web_url: str = Field(default="http://127.0.0.1:3001", alias="PUBLIC_WEB_URL")
    piper_voice_model: str | None = Field(default=None, alias="PIPER_VOICE_MODEL")
    ffmpeg_binary_path: str = Field(default="ffmpeg", alias="FFMPEG_BINARY_PATH")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_testing(self) -> bool:
        return self.app_env == "test"


@lru_cache
def get_settings() -> Settings:
    return Settings()
