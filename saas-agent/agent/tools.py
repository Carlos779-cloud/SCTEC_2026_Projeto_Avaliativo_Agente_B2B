"""Tools autorizadas para consultar o SaaS e incluir créditos extras."""

from typing import Any

import httpx
from langchain_core.tools import tool
from pydantic import TypeAdapter, ValidationError

from agent.config import settings
from agent.models import (
    AssinaturaSaaS,
    BuscarEmpresaInput,
    ConsultarAssinaturaInput,
    EmpresaSaaS,
    IncluirCreditosInput,
)


_TIMEOUT = httpx.Timeout(10.0, connect=3.0)
_BASE_URL = str(settings.solar_api_base_url).rstrip("/")
_EMPRESAS_ADAPTER = TypeAdapter(list[EmpresaSaaS])
_ASSINATURAS_ADAPTER = TypeAdapter(list[AssinaturaSaaS])


def _failure(message: str, status_code: int | None = None) -> dict[str, Any]:
    """Monta uma falha estruturada para o grafo tratar sem derrubar o agente."""
    return {"ok": False, "error": message, "status_code": status_code}


def _request_json(
    method: str,
    path: str,
    *,
    params: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
) -> tuple[Any | None, dict[str, Any] | None]:
    """Executa uma chamada HTTP limitada por timeout e converte erros comuns."""
    try:
        with httpx.Client(base_url=_BASE_URL, timeout=_TIMEOUT) as client:
            response = client.request(method, path, params=params, json=payload)
    except httpx.TimeoutException:
        return None, _failure("A API SaaS excedeu o tempo limite da chamada.")
    except httpx.RequestError:
        return None, _failure("Não foi possível conectar à API SaaS.")

    if not response.is_success:
        status_code = response.status_code
        if status_code >= 500:
            return None, _failure("A API SaaS encontrou um erro interno.", status_code)

        message = {
            404: "O recurso solicitado não foi encontrado na API SaaS.",
            422: "A API SaaS recusou os dados enviados.",
        }.get(status_code, "A API SaaS recusou a solicitação.")
        return None, _failure(message, status_code)

    try:
        return response.json(), None
    except ValueError:
        return None, _failure("A API SaaS retornou uma resposta JSON inválida.", status_code)


@tool("buscar_empresa", args_schema=BuscarEmpresaInput)
def buscar_empresa(nome: str) -> dict[str, Any]:
    """Busca empresas pelo nome fantasia; retorna os campos reais da API."""
    body, error = _request_json("GET", "/empresas", params={"nome": nome})
    if error:
        return error

    try:
        empresas = _EMPRESAS_ADAPTER.validate_python(body)
    except ValidationError:
        return _failure("A API SaaS retornou empresas em formato inesperado.")

    return {"ok": True, "data": [empresa.model_dump() for empresa in empresas]}


@tool("consultar_assinatura", args_schema=ConsultarAssinaturaInput)
def consultar_assinatura(empresa_id: int) -> dict[str, Any]:
    """Consulta a lista de assinaturas vinculadas ao ID real da empresa."""
    body, error = _request_json("GET", f"/assinaturas/{empresa_id}")
    if error:
        return error

    try:
        assinaturas = _ASSINATURAS_ADAPTER.validate_python(body)
    except ValidationError:
        return _failure("A API SaaS retornou assinaturas em formato inesperado.")

    return {"ok": True, "data": [item.model_dump() for item in assinaturas]}


@tool("incluir_creditos", args_schema=IncluirCreditosInput)
def incluir_creditos(
    assinatura_id: int,
    quantidade: int,
    motivo: str,
) -> dict[str, Any]:
    """Inclui créditos via POST; aceita de 1 a 3.000 e exige motivo."""
    body, error = _request_json(
        "POST",
        f"/assinaturas/{assinatura_id}/creditos",
        payload={"quantidade": quantidade, "motivo": motivo},
    )
    if error:
        return error

    try:
        assinatura = AssinaturaSaaS.model_validate(body)
    except ValidationError:
        return _failure("A API SaaS retornou a assinatura em formato inesperado.")

    return {"ok": True, "data": assinatura.model_dump()}


SAAS_TOOLS = [buscar_empresa, consultar_assinatura, incluir_creditos]
