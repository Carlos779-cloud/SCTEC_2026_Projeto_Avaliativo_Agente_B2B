"""Decisões de roteamento condicional do grafo, sem lógica de negócio lateral."""

from agent.state import AgentState


def apos_percepcao(state: AgentState) -> str:
    """Interrompe em falha de extração; caso contrário valida os dados extraídos."""
    return "tratar_erro" if state.get("erro") else "validar_solicitacao"


def apos_validar_solicitacao(state: AgentState) -> str:
    """Só consulta o SaaS após confirmar escopo e campos de entrada válidos."""
    if state.get("erro"):
        return "tratar_erro"
    if state.get("operacao_permitida") is False:
        return "formatar_resposta"
    return "buscar_empresa"


def apos_buscar_empresa(state: AgentState) -> str:
    """Só consulta assinatura com um único ID real retornado pelo backend."""
    if state.get("erro"):
        return "tratar_erro"
    if state.get("operacao_permitida") is False:
        return "formatar_resposta"
    return "consultar_assinatura"


def apos_consultar_assinatura(state: AgentState) -> str:
    """Envia ambiguidades ou falhas à resposta sem escolher uma assinatura."""
    if state.get("erro"):
        return "tratar_erro"
    if state.get("operacao_permitida") is False:
        return "formatar_resposta"
    return "validar_regras"


def apos_validar_regras(state: AgentState) -> str:
    """A inclusão só recebe controle quando a validação Python autorizou."""
    if state.get("erro"):
        return "tratar_erro"
    if state.get("operacao_permitida") is not True:
        return "formatar_resposta"
    if state.get("intencao") == "incluir_creditos":
        return "incluir_creditos"
    return "formatar_resposta"


def apos_incluir_creditos(state: AgentState) -> str:
    """Normaliza falha de POST ou encerra com o resultado confirmado."""
    return "tratar_erro" if state.get("erro") else "formatar_resposta"
