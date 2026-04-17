from functools import lru_cache
import json

from pydantic import AliasChoices
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        protected_namespaces=("settings_",),
    )

    app_name: str = "SentinelAI"
    app_env: str = "development"
    model_provider: str = "local"
    model_name: str = "sentinel-resume-local"
    api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openai_base_url: str = "https://api.openai.com/v1"
    ollama_base_url: str = "http://localhost:11434"
    resume_context: str = (
        "Shrish is a backend engineer focused on FastAPI, microservices, "
        "distributed systems, observability, and applied AI."
    )
    owner_telegram_ids: str = Field(
        default="123456789",
        validation_alias=AliasChoices("OWNER_TELEGRAM_IDS", "OWNER_TELEGRAM_ID"),
    )
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    health_timeout_seconds: float = 3.0
    cors_origins_json: str = Field(
        default='["https://shrish0.github.io","https://semimat-otto-undilatorily.ngrok-free.dev"]'
    )
    service_targets_json: str = Field(
        default='{"sentinel-ai":"https://sentinelai-p4xw.onrender.com","browser-mcp":"https://browser-mcp-79y4.onrender.com/health"}'
    )

    @property
    def service_targets(self) -> dict[str, str]:
        return json.loads(self.service_targets_json)

    @property
    def cors_origins(self) -> list[str]:
        return json.loads(self.cors_origins_json)

    @property
    def owner_telegram_id_set(self) -> set[int]:
        raw = self.owner_telegram_ids.strip()
        if not raw:
            return set()
        if raw.startswith("["):
            return {int(value) for value in json.loads(raw)}
        return {int(value.strip()) for value in raw.split(",") if value.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
