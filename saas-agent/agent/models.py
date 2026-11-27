"""Schemas de entrada das tools e de resposta da API SaaS."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BuscarEmpresaInput(BaseModel):
    """Entrada para localizar empresas por nome fantasia."""

    nome: str = Field(
        min_length=1,
        max_length=150,
        description="Nome fantasia informado pelo analista.",
    )

    @field_validator("nome", mode="before")
    @classmethod
    def trim_nome(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ConsultarAssinaturaInput(BaseModel):
    """Entrada para consultar as assinaturas de uma empresa existente."""

    empresa_id: Annotated[
        int,
        Field(strict=True, gt=0, description="ID real retornado pela busca de empresas."),
    ]


class IncluirCreditosInput(BaseModel):
    """Entrada para incluir créditos extras em uma assinatura."""

    assinatura_id: Annotated[
        int,
        Field(strict=True, gt=0, description="ID real da assinatura consultada."),
    ]
    quantidade: Annotated[
        int,
        Field(strict=True, gt=0, le=3000, description="Créditos inteiros, de 1 a 3.000."),
    ]
    motivo: str = Field(
        min_length=3,
        max_length=500,
        description="Justificativa operacional para a inclusão.",
    )

    @field_validator("motivo", mode="before")
    @classmethod
    def trim_motivo(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class EmpresaSaaS(BaseModel):
    """Campos efetivamente devolvidos pelo endpoint GET /empresas."""

    model_config = ConfigDict(extra="ignore")

    id: int
    nome_fantasia: str
    cnpj: str
    dominio_corporativo: str


class AssinaturaSaaS(BaseModel):
    """Campos efetivamente devolvidos pelos endpoints de assinatura."""

    model_config = ConfigDict(extra="ignore")

    id: int
    empresa_id: int
    plano: str
    status: str
    saldo_creditos_api: int
    limite_usuarios: int


class SolicitacaoExtraida(BaseModel):
    """Dados explícitos da mensagem, extraídos pelo modelo sem decidir regras."""

    intencao: Literal[
        "consultar_assinatura",
        "incluir_creditos",
        "fora_escopo",
        "ambigua",
    ] = Field(description="Intenção operacional expressa na mensagem do analista.")
    nome_empresa: str | None = Field(
        default=None,
        max_length=150,
        description="Nome fantasia informado explicitamente; nunca invente um nome.",
    )
    creditos_solicitados: int | float | str | bool | None = Field(
        default=None,
        description="Quantidade tal como expressa; preserve frações e valores inválidos.",
    )
    motivo_operacao: str | None = Field(
        default=None,
        max_length=500,
        description="Justificativa explícita para inclusão, sem inventar motivo.",
    )

    @field_validator("nome_empresa", "motivo_operacao", mode="before")
    @classmethod
    def trim_optional_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ParecerDados(BaseModel):
    """Dados conhecidos usados no JSON final da API do agente."""

    nome_empresa: str | None = None
    empresa_id: int | None = None
    assinatura_id: int | None = None
    plano: str | None = None
    status_assinatura: str | None = None
    saldo_anterior: int | None = None
    creditos_solicitados: int | float | str | bool | None = None
    creditos_incluidos: int | None = None
    saldo_atualizado: int | None = None


class ParecerFinal(BaseModel):
    """Resposta JSON validada, equivalente ao formato definido no prompt."""

    parecer: Literal["aprovado", "recusado", "erro", "aguardando_confirmacao"]
    mensagem: str
    dados: ParecerDados
    motivo_recusa: str | None = None
