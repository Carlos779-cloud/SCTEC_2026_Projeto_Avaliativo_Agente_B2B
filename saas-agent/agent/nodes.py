"""Nos do grafo: extraem, consultam, validam, agem e formatam a resposta."""

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import ValidationError

from agent.config import settings
from agent.models import ParecerFinal, SolicitacaoExtraida
from agent.prompts import PERCEPTION_SYSTEM_PROMPT
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
                SystemMessage(content=PERCEPTION_SYSTEM_PROMPT),
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
            "mensagem": "Não posso executar esta operação porque ela está fora das permissões do agente. Posso consultar empresas e assinaturas ou solicitar créditos extras, desde que todos os critérios sejam atendidos. Nenhuma alteração foi enviada ao SaaS.",
        }
    if intent == "ambigua":
        return {
            "operacao_permitida": False,
            "motivo_recusa": "intencao_ambigua",
            "parecer": "recusado",
            "mensagem": "Não consegui identificar qual operação você deseja. Informe se quer consultar uma assinatura ou solicitar créditos extras e indique o nome fantasia da empresa. Nenhuma consulta ou alteração foi realizada.",
        }
    if intent not in {"consultar_assinatura", "incluir_creditos"}:
        return _falha_controlada("A intenção da solicitação não foi reconhecida.")

    company_name = state.get("nome_empresa")
    if not isinstance(company_name, str) or not company_name.strip():
        return {
            "operacao_permitida": False,
            "motivo_recusa": "nome_empresa_ausente",
            "parecer": "recusado",
            "mensagem": "Não foi possível iniciar a consulta porque o nome fantasia da empresa não foi informado. Envie o nome da empresa e diga se deseja consultar a assinatura ou solicitar créditos extras.",
        }

    if intent == "incluir_creditos":
        quantity = state.get("creditos_solicitados")
        if type(quantity) is not int or not 1 <= quantity <= 3000:
            return {
                "operacao_permitida": False,
                "motivo_recusa": "quantidade_invalida",
                "parecer": "recusado",
                "mensagem": "Não posso validar a solicitação de créditos: a quantidade precisa ser um número inteiro de 1 a 3.000, inclusive. Informe uma quantidade dentro desse intervalo; nenhum crédito foi enviado ao SaaS.",
            }

        reason = state.get("motivo_operacao")
        if not isinstance(reason, str) or len(reason.strip()) < 3:
            return {
                "operacao_permitida": False,
                "motivo_recusa": "motivo_ausente",
                "parecer": "recusado",
                "mensagem": "Não posso solicitar a inclusão sem uma justificativa explícita. Informe o motivo da operação para que ele possa ser registrado na auditoria; nenhum crédito foi enviado ao SaaS.",
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
            "mensagem": "A busca não encontrou uma empresa correspondente ao nome informado. Confira a grafia ou envie o nome fantasia completo. O fluxo foi encerrado sem consultar uma assinatura e sem solicitar créditos.",
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
            "mensagem": f"A busca encontrou mais de uma empresa compatível: {options}. Para evitar consultar ou alterar a conta errada, informe o nome ou ID da empresa desejada. Nenhuma assinatura foi consultada e nenhum crédito foi solicitado.",
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
                "mensagem": "A empresa foi localizada, mas o SaaS não retornou uma assinatura para ela. Confirme se a empresa correta foi informada ou solicite apoio administrativo. Nenhuma inclusão de créditos foi realizada.",
            }
        return {"erro": result.get("error", "Falha ao consultar a assinatura.")}

    subscriptions = result.get("data", [])
    if not subscriptions:
        return {
            "assinaturas_encontradas": [],
            "operacao_permitida": False,
            "motivo_recusa": "assinatura_nao_encontrada",
            "parecer": "recusado",
            "mensagem": "A consulta da empresa não retornou assinaturas. Confirme os dados da empresa ou solicite apoio administrativo. Nenhuma inclusão de créditos foi realizada.",
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
            "mensagem": f"A empresa possui mais de uma assinatura: {options}. Informe qual assinatura deseja consultar; o agente não escolherá uma automaticamente. Nenhuma inclusão de créditos foi realizada.",
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
            "mensagem": f"Consulta concluída. A API SaaS retornou a empresa {state.get('nome_empresa') or 'informada'} (ID {state.get('empresa_id')}), assinatura #{state.get('assinatura_id')}, plano {state.get('plano')}, status {state.get('status_assinatura')} e saldo atual de {state.get('saldo_atual')} créditos. Esta solicitação foi somente de consulta; nenhum crédito foi incluído.",
        }

    if str(state["status_assinatura"]).strip().upper() != "ATIVA":
        return {
            "operacao_permitida": False,
            "motivo_recusa": "assinatura_inativa",
            "parecer": "recusado",
            "mensagem": f"Não posso incluir créditos porque a assinatura #{state.get('assinatura_id')} da empresa {state.get('nome_empresa') or 'informada'} está com status {state.get('status_assinatura')}, e a regra exige status ATIVA. A operação foi bloqueada antes do POST; nenhum crédito foi incluído.",
        }

    quantity = state.get("creditos_solicitados")
    if type(quantity) is not int or not 1 <= quantity <= 3000:
        return {
            "operacao_permitida": False,
            "motivo_recusa": "quantidade_invalida",
            "parecer": "recusado",
            "mensagem": "A quantidade solicitada não passou pela validação: deve ser um número inteiro entre 1 e 3.000, inclusive. Corrija a quantidade para continuar. Nenhum POST foi enviado ao SaaS.",
        }
    reason = state.get("motivo_operacao")
    if not isinstance(reason, str) or len(reason.strip()) < 3:
        return {
            "operacao_permitida": False,
            "motivo_recusa": "motivo_ausente",
            "parecer": "recusado",
            "mensagem": "A solicitação não contém uma justificativa válida para a inclusão. Informe o motivo para que seja registrado na auditoria. Nenhum POST foi enviado ao SaaS.",
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
            "mensagem": "A verificação final não confirmou todos os requisitos: assinatura identificada e ativa, quantidade inteira entre 1 e 3.000 e justificativa informada. Por segurança, o POST não foi enviado e nenhum crédito foi solicitado.",
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
                "mensagem": "A API SaaS recusou a solicitação de inclusão. A operação não foi confirmada como concluída; confira o status da assinatura, a quantidade e a justificativa antes de tentar novamente.",
            }
        return {"erro": "Não foi possível confirmar o resultado da inclusão junto ao SaaS. Consulte o saldo e a auditoria da assinatura antes de repetir a solicitação, para evitar uma inclusão duplicada."}

    updated = result.get("data", {})
    if updated.get("id") != subscription_id:
        return {"erro": "A API SaaS retornou dados de outra assinatura. Não foi possível confirmar a inclusão; confira o saldo e a auditoria antes de qualquer nova tentativa."}

    empresa = state.get("nome_empresa") or f"ID {state.get('empresa_id')}"
    plano = state.get("plano") or "não informado"
    status = state.get("status_assinatura") or "ATIVA"
    saldo_anterior = state.get("saldo_atual")
    saldo_novo = updated["saldo_creditos_api"]

    return {
        "resultado_inclusao": result,
        "creditos_incluidos": quantity,
        "saldo_atualizado": saldo_novo,
        "parecer": "aprovado",
        "mensagem": (
            f"Solicitação aprovada para a empresa {empresa} (assinatura #{subscription_id}, "
            f"plano informado {plano}, status {status}). Todos os critérios de negócio implementados foram validados "
            f"(assinatura ativa, quantidade inteira entre 1 e 3.000 e motivo "
            f"registrado: '{reason.strip()}'). A API SaaS confirmou a inclusão de {quantity} "
            f"créditos extras, atualizando o saldo de {saldo_anterior} para {saldo_novo} créditos."
        ),
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
