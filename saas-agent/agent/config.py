"""Configuracao local do agente e integracao com a API SaaS."""

from pathlib import Path

from pydantic import AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class AgentSettings(BaseSettings):
    """Configuracoes carregadas do ambiente e de ``saas-agent/.env``."""

    groq_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="Chave da API Groq; nunca deve ser registrada em logs.",
    )
    llm_model: str = Field(
        default="openai/gpt-oss-120b",
        min_length=1,
        description="Identificador do modelo Groq configurado para o agente.",
    )
    agent_max_iterations: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Limite de chamadas externas por execucao do grafo.",
    )

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
