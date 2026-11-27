"""API REST do agente de consulta de assinaturas e créditos extras."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator

from agent.graph import executar_agente
from agent.models import ParecerFinal


class ConsultaRequest(BaseModel):
    """Corpo da solicitação HTTP enviada pelo analista."""

    mensagem: str = Field(
        min_length=1,
        max_length=4000,
        description="Solicitação em linguagem natural para o agente CS B2B.",
    )

    @field_validator("mensagem", mode="before")
    @classmethod
    def trim_mensagem(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class HealthResponse(BaseModel):
    status: Literal["ok"]


app = FastAPI(
    title="SCTEC SaaS B2B Agent API",
    description=(
        "API do agente de Customer Success para consultar empresas e assinaturas "
        "e solicitar créditos extras sob validação determinística."
    ),
    version="0.1.0",
)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    """Confirma que o processo HTTP do agente está respondendo."""
    return HealthResponse(status="ok")


@app.post(
    "/consultar",
    response_model=ParecerFinal,
    summary="Processa uma solicitação operacional de CS B2B",
    tags=["agente"],
)
def consultar(request: ConsultaRequest) -> ParecerFinal:
    """Executa o grafo e devolve somente o parecer público validado."""
    result = executar_agente(request.mensagem)
    return ParecerFinal.model_validate(result)
