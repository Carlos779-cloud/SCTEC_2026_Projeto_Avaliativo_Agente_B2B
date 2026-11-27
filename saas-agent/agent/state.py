"""Estado tipado compartilhado pelos nós do grafo do agente.

Os nós retornam somente os campos que alteram. O reducer ``add_messages``
acrescenta mensagens ao histórico; os demais campos operacionais são
substituídos pelo valor informado no update.

Responsabilidades previstas:
- perceber: ``intencao``, ``nome_empresa`` e ``creditos_solicitados``;
- buscar empresa: ``empresas_encontradas`` e ``empresa_id`` quando única;
- consultar assinatura: ``assinaturas_encontradas`` e dados da assinatura
  confirmada;
- validar: ``operacao_permitida``, ``motivo_recusa`` e confirmação opcional;
- incluir: ``resultado_inclusao``, ``creditos_incluidos`` e saldo atualizado;
- tratar erro: ``erro``;
- formatar: ``parecer``, ``mensagem`` e ``resposta_final``.
"""

from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph.message import add_messages


Parecer = Literal["aprovado", "recusado", "erro", "aguardando_confirmacao"]
EstadoConfirmacao = Literal["nao_necessaria", "pendente", "aprovada", "recusada"]
CreditoSolicitado = int | float | str | bool | None


class AgentState(TypedDict, total=False):
    """Estado da execução, separado entre mensagens e dados operacionais.

    Campos de consulta e resultado iniciam como ``None`` ou lista vazia;
    ``iteracoes`` inicia em zero. ``creditos_solicitados`` também aceita tipos
    inválidos para que o nó de validação os recuse sem coerção silenciosa.
    """

    # Conversa: o reducer mantém o histórico e processa atualizações de mensagens.
    messages: Annotated[list[AnyMessage], add_messages]

    # Percepção da solicitação.
    intencao: str | None
    nome_empresa: str | None
    creditos_solicitados: CreditoSolicitado

    # Resultados de localização e consulta; listas preservam possíveis ambiguidades.
    empresas_encontradas: list[dict[str, Any]]
    empresa_id: int | None
    assinaturas_encontradas: list[dict[str, Any]]
    assinatura_id: int | None
    plano: str | None
    status_assinatura: str | None
    saldo_atual: int | None

    # Validação, ação e confirmação humana opcional.
    operacao_permitida: bool | None
    motivo_recusa: str | None
    estado_confirmacao: EstadoConfirmacao
    resultado_inclusao: dict[str, Any] | None
    creditos_incluidos: int | None
    saldo_atualizado: int | None

    # Controle de execução e resposta pública.
    iteracoes: int
    erro: str | None
    parecer: Parecer | None
    mensagem: str | None
    resposta_final: dict[str, Any] | None


def criar_estado_inicial(mensagem_usuario: str) -> AgentState:
    """Cria o estado inicial com a mensagem do usuário e valores operacionais vazios."""
    mensagem_limpa = mensagem_usuario.strip()
    if not mensagem_limpa:
        raise ValueError("A mensagem do usuário não pode estar vazia.")

    return {
        "messages": [HumanMessage(content=mensagem_limpa)],
        "intencao": None,
        "nome_empresa": None,
        "creditos_solicitados": None,
        "empresas_encontradas": [],
        "empresa_id": None,
        "assinaturas_encontradas": [],
        "assinatura_id": None,
        "plano": None,
        "status_assinatura": None,
        "saldo_atual": None,
        "operacao_permitida": None,
        "motivo_recusa": None,
        "estado_confirmacao": "nao_necessaria",
        "resultado_inclusao": None,
        "creditos_incluidos": None,
        "saldo_atualizado": None,
        "iteracoes": 0,
        "erro": None,
        "parecer": None,
        "mensagem": None,
        "resposta_final": None,
    }
