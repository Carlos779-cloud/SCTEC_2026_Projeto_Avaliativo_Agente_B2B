"""Montagem e execução do StateGraph do agente B2B."""

from collections.abc import Callable
from functools import wraps
from typing import Any

from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph

from agent.config import settings
from agent.models import ParecerDados, ParecerFinal
from agent.nodes import (
    buscar_empresa_node,
    consultar_assinatura_node,
    formatar_resposta,
    incluir_creditos_node,
    perceber_intencao,
    tratar_erro,
    validar_regras,
    validar_solicitacao,
)
from agent.routing import (
    apos_buscar_empresa,
    apos_consultar_assinatura,
    apos_incluir_creditos,
    apos_percepcao,
    apos_validar_regras,
    apos_validar_solicitacao,
)
from agent.state import AgentState, criar_estado_inicial


def _com_limite_de_iteracoes(node: Callable[[AgentState], dict[str, Any]]):
    """Conta chamadas externas e encerra com erro controlado ao atingir o limite."""

    @wraps(node)
    def counted_node(state: AgentState) -> dict[str, Any]:
        current = state.get("iteracoes", 0)
        if current >= settings.agent_max_iterations:
            return {
                "iteracoes": current,
                "erro": "O limite de chamadas externas desta execução foi atingido.",
                "operacao_permitida": False,
            }

        try:
            update = node(state)
        except Exception:
            update = {
                "erro": "Ocorreu um erro não recuperável ao consultar um serviço externo.",
                "operacao_permitida": False,
            }
        return {**update, "iteracoes": current + 1}

    return counted_node


def construir_grafo():
    """Cria e compila o grafo com roteamento condicional e guardas de inclusão."""
    builder = StateGraph(AgentState)

    # Apenas estes nós chamam um serviço externo (modelo ou SaaS) e contam no limite.
    builder.add_node("perceber", _com_limite_de_iteracoes(perceber_intencao))
    builder.add_node("validar_solicitacao", validar_solicitacao)
    builder.add_node("buscar_empresa", _com_limite_de_iteracoes(buscar_empresa_node))
    builder.add_node(
        "consultar_assinatura",
        _com_limite_de_iteracoes(consultar_assinatura_node),
    )
    builder.add_node("validar_regras", validar_regras)
    builder.add_node("incluir_creditos", _com_limite_de_iteracoes(incluir_creditos_node))
    builder.add_node("tratar_erro", tratar_erro)
    builder.add_node("formatar_resposta", formatar_resposta)

    builder.add_edge(START, "perceber")
    builder.add_conditional_edges(
        "perceber",
        apos_percepcao,
        {"tratar_erro": "tratar_erro", "validar_solicitacao": "validar_solicitacao"},
    )
    builder.add_conditional_edges(
        "validar_solicitacao",
        apos_validar_solicitacao,
        {
            "tratar_erro": "tratar_erro",
            "formatar_resposta": "formatar_resposta",
            "buscar_empresa": "buscar_empresa",
        },
    )
    builder.add_conditional_edges(
        "buscar_empresa",
        apos_buscar_empresa,
        {
            "tratar_erro": "tratar_erro",
            "formatar_resposta": "formatar_resposta",
            "consultar_assinatura": "consultar_assinatura",
        },
    )
    builder.add_conditional_edges(
        "consultar_assinatura",
        apos_consultar_assinatura,
        {
            "tratar_erro": "tratar_erro",
            "formatar_resposta": "formatar_resposta",
            "validar_regras": "validar_regras",
        },
    )
    builder.add_conditional_edges(
        "validar_regras",
        apos_validar_regras,
        {
            "tratar_erro": "tratar_erro",
            "formatar_resposta": "formatar_resposta",
            "incluir_creditos": "incluir_creditos",
        },
    )
    builder.add_conditional_edges(
        "incluir_creditos",
        apos_incluir_creditos,
        {"tratar_erro": "tratar_erro", "formatar_resposta": "formatar_resposta"},
    )
    builder.add_edge("tratar_erro", "formatar_resposta")
    builder.add_edge("formatar_resposta", END)

    return builder.compile()


agent_graph = construir_grafo()


def executar_agente(mensagem_usuario: str) -> dict[str, Any]:
    """Executa uma solicitação e sempre devolve o parecer JSON validado."""
    recursion_limit = max(12, settings.agent_max_iterations * 2 + 10)

    try:
        initial_state = criar_estado_inicial(mensagem_usuario)
        result = agent_graph.invoke(
            initial_state,
            config={"recursion_limit": recursion_limit},
        )
        response = result.get("resposta_final")
        if response is None:
            raise RuntimeError("O grafo terminou sem montar a resposta final.")
        return ParecerFinal.model_validate(response).model_dump(mode="json")
    except ValueError:
        return ParecerFinal(
            parecer="recusado",
            mensagem="Envie uma solicitação com o nome fantasia da empresa e a operação desejada.",
            dados=ParecerDados(),
            motivo_recusa="mensagem_vazia",
        ).model_dump(mode="json")
    except GraphRecursionError:
        message = "O limite de execução do grafo foi atingido; a solicitação foi encerrada com segurança."
    except Exception:
        message = "Não foi possível concluir a solicitação devido a um erro interno do agente."

    return ParecerFinal(
        parecer="erro",
        mensagem=message,
        dados=ParecerDados(),
    ).model_dump(mode="json")
