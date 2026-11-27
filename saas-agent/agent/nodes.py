"""Nos do grafo: extraem, consultam, validam, agem e formatam a resposta."""

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import ValidationError

from agent.config import settings
from agent.models import ParecerFinal, SolicitacaoExtraida
from agent.prompts import SYSTEM_PROMPT
from agent.state import AgentState
from agent.tools import buscar_empresa, consultar_assinatura, incluir_creditos


def _falha_controlada(message: str) -> dict[str, Any]:
    """Cria um update de erro sem incluir detalhes internos ou credenciais."""
    return {"erro": message, "operacao_permitida": False}


def perceber_intencao(state: AgentState) -> dict[str, Any]:
    """Extrai somente os dados explícitos da mensagem; não decide permissões."""
    user_message = next(
        (message for message in reversed(state.get("messages", [])) if isinstance(message, HumanMessage)),
        None,
    )
    if user_message is None or not isinstance(user_message.content, str):
        return _falha_controlada("Não encontrei uma mensagem válida do analista.")

    api_key = settings.groq_api_key.get_secret_value()
    if not api_key:
        return _falha_controlada("A chave GROQ_API_KEY não está configurada no ambiente do agente.")

    try:
        model = ChatGroq(
            api_key=api_key,
            model=settings.llm_model,
            temperature=0.0,
            timeout=20.0,
            max_retries=1,
        )
        extractor = model.with_structured_output(SolicitacaoExtraida)
        extracted = extractor.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_message.content),
            ]
        )
        request = SolicitacaoExtraida.model_validate(extracted)
    except (ValidationError, ValueError):
        return _falha_controlada("Não consegui interpretar a solicitação em um formato válido.")
    except Exception:
        return _falha_controlada("O modelo de linguagem não conseguiu processar a solicitação.")

    return request.model_dump()


def validar_solicitacao(state: AgentState) -> dict[str, Any]:
    """Recusa escopo inválido e dados obrigatórios ausentes antes de consultar o SaaS."""
    intent = state.get("intencao")
    if intent == "fora_escopo":
        return {
            "operacao_permitida": False,
            "motivo_recusa": "solicitacao_fora_do_escopo",
            "parecer": "recusado",
            "mensagem": "Posso consultar empresas e assinaturas ou solicitar créditos extras conforme as regras. Esta solicitação está fora desse escopo.",
        }
    if intent == "ambigua":
        return {
            "operacao_permitida": False,
            "motivo_recusa": "intencao_ambigua",
            "parecer": "recusado",
            "mensagem": "Não consegui identificar se você deseja consultar uma assinatura ou solicitar créditos. Esclareça a operação.",
        }
    if intent not in {"consultar_assinatura", "incluir_creditos"}:
        return _falha_controlada("A intenção da solicitação não foi reconhecida.")

    company_name = state.get("nome_empresa")
    if not isinstance(company_name, str) or not company_name.strip():
        return {
            "operacao_permitida": False,
            "motivo_recusa": "nome_empresa_ausente",
            "parecer": "recusado",
            "mensagem": "Informe o nome fantasia da empresa para eu localizar a assinatura.",
        }

    if intent == "incluir_creditos":
        quantity = state.get("creditos_solicitados")
        if type(quantity) is not int or not 1 <= quantity <= 3000:
            return {
                "operacao_permitida": False,
                "motivo_recusa": "quantidade_invalida",
                "parecer": "recusado",
                "mensagem": "A quantidade deve ser um número inteiro entre 1 e 3.000 créditos, inclusive.",
            }

        reason = state.get("motivo_operacao")
        if not isinstance(reason, str) or len(reason.strip()) < 3:
            return {
                "operacao_permitida": False,
                "motivo_recusa": "motivo_ausente",
                "parecer": "recusado",
                "mensagem": "Informe o motivo da inclusão de créditos para que a operação possa ser registrada na auditoria.",
            }

    return {"operacao_permitida": None}


def buscar_empresa_node(state: AgentState) -> dict[str, Any]:
    """Localiza a empresa e só guarda seu ID quando há um único resultado."""
    result = buscar_empresa.invoke({"nome": state["nome_empresa"]})
    if not result.get("ok"):
        return {"erro": result.get("error", "Falha ao buscar a empresa.")}

    companies = result.get("data", [])
    if not companies:
        return {
            "empresas_encontradas": [],
            "operacao_permitida": False,
            "motivo_recusa": "empresa_nao_encontrada",
            "parecer": "recusado",
            "mensagem": "Não encontrei uma empresa com esse nome fantasia.",
        }
    if len(companies) > 1:
        options = "; ".join(
            f"{company['nome_fantasia']} (ID {company['id']})" for company in companies
        )
        return {
            "empresas_encontradas": companies,
            "operacao_permitida": False,
            "motivo_recusa": "empresa_ambigua",
            "parecer": "recusado",
            "mensagem": f"Encontrei mais de uma empresa compatível: {options}. Informe qual delas deseja consultar.",
        }

    company = companies[0]
    return {
        "empresas_encontradas": companies,
        "empresa_id": company["id"],
        "nome_empresa": company["nome_fantasia"],
    }


def consultar_assinatura_node(state: AgentState) -> dict[str, Any]:
    """Consulta e aceita a assinatura somente quando o resultado não é ambíguo."""
    result = consultar_assinatura.invoke({"empresa_id": state["empresa_id"]})
    if not result.get("ok"):
        if result.get("status_code") == 404:
            return {
                "erro": None,
                "operacao_permitida": False,
                "motivo_recusa": "assinatura_nao_encontrada",
                "parecer": "recusado",
                "mensagem": "A API não encontrou uma assinatura para essa empresa.",
            }
        return {"erro": result.get("error", "Falha ao consultar a assinatura.")}

    subscriptions = result.get("data", [])
    if not subscriptions:
        return {
            "assinaturas_encontradas": [],
            "operacao_permitida": False,
            "motivo_recusa": "assinatura_nao_encontrada",
            "parecer": "recusado",
            "mensagem": "Não encontrei uma assinatura para essa empresa.",
        }
    if len(subscriptions) > 1:
        options = "; ".join(
            f"assinatura {item['id']} ({item['plano']}, status {item['status']})"
            for item in subscriptions
        )
        return {
            "assinaturas_encontradas": subscriptions,
            "operacao_permitida": False,
            "motivo_recusa": "assinatura_ambigua",
            "parecer": "recusado",
            "mensagem": f"A empresa possui mais de uma assinatura: {options}. Esclareça qual deseja consultar.",
        }

    subscription = subscriptions[0]
    return {
        "assinaturas_encontradas": subscriptions,
        "assinatura_id": subscription["id"],
        "plano": subscription["plano"],
        "status_assinatura": subscription["status"],
        "saldo_atual": subscription["saldo_creditos_api"],
    }


def validar_regras(state: AgentState) -> dict[str, Any]:
    """Aplica as regras determinísticas antes de permitir qualquer inclusão."""
    required = ("assinatura_id", "plano", "status_assinatura", "saldo_atual")
    if any(state.get(field) is None for field in required):
        return _falha_controlada("A consulta não retornou todos os dados necessários da assinatura.")

    if state.get("intencao") == "consultar_assinatura":
        return {
            "operacao_permitida": True,
            "parecer": "aprovado",
            "mensagem": "Consulta concluída com os dados retornados pela API SaaS.",
        }

    if str(state["status_assinatura"]).strip().upper() != "ATIVA":
        return {
            "operacao_permitida": False,
            "motivo_recusa": "assinatura_inativa",
            "parecer": "recusado",
            "mensagem": "A assinatura não está ativa; nenhuma inclusão de créditos foi realizada.",
        }

    quantity = state.get("creditos_solicitados")
    if type(quantity) is not int or not 1 <= quantity <= 3000:
        return {
            "operacao_permitida": False,
            "motivo_recusa": "quantidade_invalida",
            "parecer": "recusado",
            "mensagem": "A quantidade deve ser um número inteiro entre 1 e 3.000 créditos, inclusive.",
        }
    reason = state.get("motivo_operacao")
    if not isinstance(reason, str) or len(reason.strip()) < 3:
        return {
            "operacao_permitida": False,
            "motivo_recusa": "motivo_ausente",
            "parecer": "recusado",
            "mensagem": "Informe o motivo da inclusão para registro de auditoria.",
        }

    return {"operacao_permitida": True}


def incluir_creditos_node(state: AgentState) -> dict[str, Any]:
    """Faz a última barreira determinística imediatamente antes do POST."""
    quantity = state.get("creditos_solicitados")
    reason = state.get("motivo_operacao")
    subscription_id = state.get("assinatura_id")
    if (
        state.get("operacao_permitida") is not True
        or type(subscription_id) is not int
        or subscription_id <= 0
        or str(state.get("status_assinatura", "")).strip().upper() != "ATIVA"
        or type(quantity) is not int
        or not 1 <= quantity <= 3000
        or not isinstance(reason, str)
        or len(reason.strip()) < 3
    ):
        return {
            "operacao_permitida": False,
            "motivo_recusa": "validacao_final_reprovada",
            "parecer": "recusado",
            "mensagem": "A validação final não autorizou a inclusão. Nenhum crédito foi enviado ao SaaS.",
        }

    result = incluir_creditos.invoke(
        {
            "assinatura_id": subscription_id,
            "quantidade": quantity,
            "motivo": reason.strip(),
        }
    )
    if not result.get("ok"):
        if result.get("status_code") == 422:
            return {
                "operacao_permitida": False,
                "motivo_recusa": "api_recusou_operacao",
                "parecer": "recusado",
                "mensagem": "A API SaaS recusou a inclusão; não foi confirmada como concluída.",
            }
        return {"erro": result.get("error", "Falha ao incluir créditos no SaaS.")}

    updated = result.get("data", {})
    if updated.get("id") != subscription_id:
        return {"erro": "A API SaaS retornou uma assinatura diferente da solicitada; não foi possível confirmar o resultado."}

    return {
        "resultado_inclusao": result,
        "creditos_incluidos": quantity,
        "saldo_atualizado": updated["saldo_creditos_api"],
        "parecer": "aprovado",
        "mensagem": "A API SaaS confirmou a inclusão dos créditos extras.",
    }


def tratar_erro(state: AgentState) -> dict[str, Any]:
    """Normaliza falhas externas em um parecer controlado para o analista."""
    message = state.get("erro") or "Ocorreu um erro não recuperável durante a operação."
    return {
        "operacao_permitida": False,
        "parecer": "erro",
        "mensagem": message,
    }


def formatar_resposta(state: AgentState) -> dict[str, Any]:
    """Valida e grava o JSON final, incluindo apenas dados conhecidos."""
    opinion = state.get("parecer") or "erro"
    message = state.get("mensagem") or "Não foi possível concluir a solicitação."
    final = ParecerFinal.model_validate(
        {
            "parecer": opinion,
            "mensagem": message,
            "motivo_recusa": state.get("motivo_recusa"),
            "dados": {
                "nome_empresa": state.get("nome_empresa"),
                "empresa_id": state.get("empresa_id"),
                "assinatura_id": state.get("assinatura_id"),
                "plano": state.get("plano"),
                "status_assinatura": state.get("status_assinatura"),
                "saldo_anterior": state.get("saldo_atual"),
                "creditos_solicitados": state.get("creditos_solicitados"),
                "creditos_incluidos": state.get("creditos_incluidos"),
                "saldo_atualizado": state.get("saldo_atualizado"),
            },
        }
    )
    response = final.model_dump(mode="json")
    return {
        "resposta_final": response,
        "messages": [AIMessage(content=json.dumps(response, ensure_ascii=False))],
    }
