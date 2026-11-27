"""Configuracao local do agente e integracao com a API SaaS."""

from pathlib import Path

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class AgentSettings(BaseSettings):
    """Configuracoes carregadas do ambiente e de ``saas-agent/.env``."""

    solar_api_base_url: AnyHttpUrl = Field(
        default="http://localhost:8002",
        description="URL base da API SaaS administrativa.",
    )

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = AgentSettings()
