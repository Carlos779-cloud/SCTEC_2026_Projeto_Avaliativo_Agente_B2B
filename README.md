# SCTEC_2026_Projeto_Avaliativo_Agente_B2B

**Link para clonar o repositório:** `[INSERIR LINK DO GIT CLONE]`  
**Link do vídeo de demonstração:** `[INSERIR LINK DO VÍDEO]`

## Objetivo

O agente atende analistas de Customer Success B2B. Ele consulta empresas e assinaturas no SaaS administrativo e pode solicitar créditos extras somente quando as validações de negócio forem aprovadas.

O sistema é dividido em dois serviços locais:

- `api-saas`: API administrativa FastAPI com banco PostgreSQL em Docker Compose; padrão local `http://localhost:8002`.
- `saas-agent`: agente LangChain/LangGraph exposto por FastAPI; padrão local `http://127.0.0.1:8001`.

## Pré-requisitos no Windows

- Windows 10/11 com PowerShell.
- Python 3.12 ou superior. O ambiente virtual usado para esta entrega executou **Python 3.14.7** (`uv run python --version`).
- [`uv`](https://docs.astral.sh/uv/) para resolver e sincronizar as dependências do agente.
- Docker Desktop com Docker Compose v2 para executar o SaaS e PostgreSQL.
- Uma chave válida do provedor Groq para executar a percepção real do modelo.

O `pyproject.toml` declara `requires-python = ">=3.12"`; portanto, Python 3.14.7 é a versão observada neste ambiente, não a única versão suportada.

## Pré-requisitos no Linux

- Distribuição Linux 64-bit atual, com Bash e `git`.
- Python 3.12 ou superior. Para reproduzir a versão usada nesta entrega, instale Python 3.14 com `uv`.
- [`uv`](https://docs.astral.sh/uv/) para instalar e sincronizar as dependências do agente.
- Docker Engine e Docker Compose v2 (plugin `docker compose`) para iniciar o SaaS e o PostgreSQL. O usuário precisa ter permissão para executar Docker.
- `curl` para verificações e para enviar uma requisição de exemplo.
- Uma chave válida do provedor Groq para executar a percepção real do modelo.

Em Ubuntu/Debian, instale Git, curl e Docker Engine/Compose conforme a documentação oficial da sua distribuição e do Docker. A instalação varia entre distribuições; confirme que `docker compose version` funciona antes de continuar.

## Clonar o projeto

Substitua o marcador pelo link Git informado no início deste documento:

```powershell
git clone <LINK_DO_GIT_CLONE>
cd SCTEC_2026_Projeto_Avaliativo_Agente_B2B
```

## Configurar o agente

Execute os comandos a partir da raiz do repositório:

```powershell
cd .\saas-agent
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
uv lock --check
uv sync --locked
uv run python --version
```

Preencha `GROQ_API_KEY` no `.env` com uma chave válida da sua conta Groq. Confira também se `LLM_MODEL` corresponde a um modelo disponível para essa conta. O `.env.example` contém somente configurações de exemplo; não coloque chaves reais nele.

| Variável | Finalidade |
| --- | --- |
| `GROQ_API_KEY` | Credencial usada pelo nó de percepção do modelo. |
| `LLM_MODEL` | Identificador do modelo configurado no Groq. |
| `SOLAR_API_BASE_URL` | URL base do SaaS administrativo; no ambiente local, `http://localhost:8002`. |
| `AGENT_MAX_ITERATIONS` | Limite de chamadas externas do grafo; no exemplo, `10`. |

O agente lê o `.env` localizado na pasta `saas-agent`. O `.gitignore` raiz ignora arquivos `.env`; mantenha a chave somente nesse arquivo local.

## Listar modelos disponíveis na Groq

O script `saas-agent/listar_modelos.py` usa a chave configurada em `saas-agent/.env` e imprime os IDs retornados pela API Groq. Ele pode ser executado a partir da raiz do repositório:

Windows PowerShell:

```powershell
cd .\saas-agent
uv run python .\listar_modelos.py
```

Linux Bash:

```bash
cd saas-agent
uv run python listar_modelos.py
```

O script lista os modelos visíveis para a chave; confirme que o ID escolhido em `LLM_MODEL` é compatível com geração de texto antes de usá-lo no agente.

## Executar os serviços

### 1. Iniciar o SaaS e PostgreSQL

Abra um terminal PowerShell na raiz do repositório:

```powershell
cd .\api-saas
docker compose up -d --build
Invoke-RestMethod -Uri http://localhost:8002/health
```

A resposta esperada do health check é `status: ok`. A API disponibiliza o Swagger em `http://localhost:8002/docs`. Na primeira inicialização, a migration cria as tabelas e carrega a massa de demonstração.

### 2. Iniciar a API do agente

Abra um segundo terminal PowerShell na raiz do repositório:

```powershell
cd .\saas-agent
uv run uvicorn api.server:app --host 127.0.0.1 --port 8001
```

A API do agente disponibiliza o Swagger em `http://127.0.0.1:8001/docs` e o health check em `http://127.0.0.1:8001/health`.

### 3. Enviar uma consulta pelo PowerShell

Com os dois serviços em execução, use um terceiro terminal:

```powershell
$body = @{ mensagem = 'Consulte a assinatura da empresa Log.' } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8001/consultar -Method Post -ContentType 'application/json' -Body $body
```

`Log` é um filtro parcial que localiza `Logística Sul` na base de demonstração. A resposta é JSON com `parecer`, `mensagem`, `dados` e `motivo_recusa`.

## Executar no Linux (Bash)

Os comandos abaixo partem da raiz do repositório clonado.

### 1. Clonar e preparar o agente

```bash
git clone <LINK_DO_GIT_CLONE>
cd SCTEC_2026_Projeto_Avaliativo_Agente_B2B/saas-agent
uv python install 3.14
cp .env.example .env
nano .env
uv lock --check
uv sync --locked
uv run python --version
```

No `.env`, preencha `GROQ_API_KEY` com a sua chave. Se o arquivo `.env` já existir, edite-o; não o sobrescreva com `cp`.

### 2. Iniciar o SaaS e PostgreSQL

Abra outro terminal Bash na raiz do repositório:

```bash
cd api-saas
docker compose up -d --build
curl --fail http://localhost:8002/health
```

A API do SaaS fica em `http://localhost:8002` e o Swagger em `http://localhost:8002/docs`.

### 3. Iniciar a API do agente

Abra um segundo terminal Bash na raiz do repositório:

```bash
cd saas-agent
uv run uvicorn api.server:app --host 127.0.0.1 --port 8001
```

O Swagger do agente fica em `http://127.0.0.1:8001/docs`. Para verificar o health check em outro terminal:

```bash
curl --fail http://127.0.0.1:8001/health
```

### 4. Enviar uma consulta

```bash
curl --fail http://127.0.0.1:8001/consultar \
  -H 'Content-Type: application/json' \
  -d '{"mensagem":"Consulte a assinatura da empresa Log."}'
```

Para parar o agente, use `Ctrl+C` no terminal em que ele está executando. Para parar os containers e preservar os dados:

```bash
cd api-saas
docker compose stop
```

`docker compose down -v` remove o volume e apaga os dados locais; use somente se quiser recriar a base do zero.

## Instalação alternativa com pip

O `requirements.txt` da raiz é uma exportação com versões fixadas das dependências do agente, gerada a partir de `saas-agent/uv.lock`. A forma recomendada continua sendo `uv sync --locked`, que mantém a instalação ligada ao arquivo de lock. Use os comandos abaixo se precisar instalar com `pip`; não é necessário instalar os dois métodos no mesmo ambiente.

Use Python 3.12 ou superior. Em Ubuntu/Debian, instale também o pacote `python3-venv` se o módulo `venv` não estiver disponível.

### Windows PowerShell

Partindo da raiz do repositório:

```powershell
cd .\saas-agent
py -3 -m venv .venv
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r ..\requirements.txt
```

Para iniciar o agente sem `uv`, ainda na pasta `saas-agent`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.server:app --host 127.0.0.1 --port 8001
```

### Linux (Bash)

Partindo da raiz do repositório:

```bash
cd saas-agent
python3 -m venv .venv
test -f .env || cp .env.example .env
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r ../requirements.txt
```

Para iniciar o agente sem `uv`, ainda na pasta `saas-agent`:

```bash
./.venv/bin/python -m uvicorn api.server:app --host 127.0.0.1 --port 8001
```

Edite o `.env` para preencher `GROQ_API_KEY` antes de iniciar o agente. O `requirements.txt` cobre somente o serviço `saas-agent`; o serviço `api-saas` continua sendo iniciado pelo Docker Compose.

## APIs e contratos usados

| Serviço | Método e rota | Uso |
| --- | --- | --- |
| Agente | `GET /health` | Confirma que o processo FastAPI do agente responde. |
| Agente | `POST /consultar` | Recebe `{"mensagem": "..."}` e devolve o parecer validado por Pydantic. |
| SaaS | `GET /health` | Confirma que a API administrativa responde. |
| SaaS | `GET /empresas?nome=...` | Busca empresas por trecho do nome fantasia. |
| SaaS | `GET /assinaturas/{empresa_id}` | Retorna a lista de assinaturas da empresa. |
| SaaS | `POST /assinaturas/{assinatura_id}/creditos` | Inclui créditos com `quantidade` e `motivo`; o backend devolve a assinatura atualizada. |

O agente não utiliza o `PATCH /assinaturas/{assinatura_id}` do SaaS nem concede permissões para atualizar planos, cancelar contratos, excluir empresas ou editar cadastros.

## Fluxo e arquitetura

1. `api/server.py` valida a mensagem HTTP e chama `executar_agente`.
2. `agent/graph.py` compila e executa o `StateGraph`, aplica `recursion_limit` e coordena os nós.
3. `agent/nodes.py` faz a extração estruturada com Groq, consulta as ferramentas, valida as regras em Python e formata o parecer.
4. `agent/routing.py` escolhe as próximas etapas do fluxo e encerra em recusa, erro ou ambiguidade.
5. `agent/state.py` mantém separadamente o histórico de mensagens e os dados operacionais.
6. `agent/tools.py` chama o SaaS via HTTPX com timeout; `agent/models.py` define os schemas Pydantic e `agent/config.py` carrega a configuração.

O nó de percepção só extrai intenção, empresa, quantidade e justificativa explícitas. A permissão de incluir créditos é decidida pelo código: há validação da solicitação, verificação da empresa/assinatura e uma última barreira imediatamente antes do POST.

## Regras e limites operacionais

- A quantidade deve ser um inteiro de **1 a 3.000**, inclusive. Quantidades ausentes, fracionárias, zero, negativas ou acima do limite são recusadas antes do POST.
- A inclusão só é permitida para assinatura com status confirmado `ATIVA`.
- O código não escolhe automaticamente entre empresas ou assinaturas ambíguas; solicita esclarecimento.
- O endpoint do SaaS exige `motivo` para registrar a inclusão na auditoria. O agente solicita uma justificativa explícita e não inventa uma.
- O agente só informa inclusão concluída quando recebe confirmação positiva do SaaS.
- As chamadas HTTP ao SaaS têm timeout de conexão de 3 segundos e timeout total de 10 segundos. A chamada ao modelo tem timeout configurado de 20 segundos.
- O limite do grafo é controlado por `AGENT_MAX_ITERATIONS` e por `recursion_limit`.

## Massa de demonstração

Em uma base criada do zero, a migration inicial carrega estes registros:

| Empresa | ID | Assinatura | Plano | Status inicial | Saldo inicial |
| --- | ---: | ---: | --- | --- | ---: |
| Logística Sul | 1 | 10 | STARTER | ATIVA | 1.200 |
| TechFlow Soluções | 2 | 11 | PRO | INATIVA | 300 |
| Alpha Varejo Brasil | 3 | 12 | STARTER | ATIVA | 500 |
| Alpha Cloud Sistemas | 4 | 13 | ENTERPRISE | ATIVA | 10.000 |

O volume Docker preserva os dados entre reinicializações. Portanto, uma base já usada pode ter saldos e auditoria diferentes dos valores iniciais.

## Evidências de execução — Etapa 7

Os cenários abaixo foram executados em 27/11/2026. As respostas de recusa vieram por `/consultar`; os casos sem POST mantiveram o saldo e a auditoria.

| Cenário | Resultado observado |
| --- | --- |
| Health da API do agente e do SaaS | Ambos responderam HTTP 200 com `status: ok`. |
| Consulta com Groq real | Consulta da empresa `Log` retornou empresa ID 1, assinatura ID 10, status `ATIVA` e saldo 2.700. A auditoria permaneceu com 2 registros. |
| Fora de escopo com Groq real | Pedido de cancelamento foi recusado após ajuste do prompt de percepção; nenhum crédito foi incluído. |
| Empresa ambígua com Groq real | Busca por `Alpha` encontrou duas empresas e pediu esclarecimento; nenhuma inclusão. |
| Empresa inexistente com Groq real | Pedido recusado com `empresa_nao_encontrada`; nenhuma inclusão. |
| Quantidade acima do limite com Groq real | Pedido de 5.000 foi recusado com `quantidade_invalida`; nenhuma inclusão. |
| Quantidade fracionária com Groq real | Pedido de 1,5 foi recusado com `quantidade_invalida`; nenhuma inclusão. |
| Assinatura inativa com Groq real | TechFlow foi recusada com status `INATIVA`; nenhuma inclusão. |
| POST nominal real ao SaaS | Com a extração estruturada simulada e o restante do fluxo real, foram incluídos 1.500 créditos na assinatura 10: saldo de 1.200 para 2.700 e auditoria de 1 para 2 registros (`INCLUSAO_CREDITOS`). |

**Limite da evidência nominal:** o POST real foi exercitado pelo grafo e pela API local do agente até o SaaS, mas com a extração simulada para controlar os dados do teste. O caminho de consulta e recusa foi testado separadamente com Groq real; não foi executado um POST nominal usando o Groq real no mesmo fluxo.

Na base local usada nesta entrega, a inclusão de teste permanece registrada: assinatura 10 está com saldo 2.700 e a auditoria contém o evento `INCLUSAO_CREDITOS`. Uma nova instalação com volume vazio começa com o seed inicial acima.

## Segurança e riscos conhecidos

- O texto da solicitação é enviado ao provedor Groq configurado para extração. Não envie segredos ou dados pessoais desnecessários na mensagem.
- O `.env` contém a chave do provedor e deve permanecer local; não o copie para o `.env.example` nem o publique.
- A API do agente não implementa autenticação de usuário. O comando de execução recomendado vincula o servidor a `127.0.0.1`; não o exponha numa rede pública sem controles adicionais.
- O POST modifica saldo e cria auditoria na base local. Use a massa de demonstração para validação; não repita o cenário nominal sem considerar o estado persistente do volume.
- `docker compose down` para e remove containers, mas preserva o volume. `docker compose down -v` apaga o volume e os dados locais; use somente se realmente quiser recriar a base vazia.

## Parar os serviços

No terminal de cada servidor, use `Ctrl+C` para parar a API do agente. Para parar os containers SaaS mantendo o volume:

```powershell
cd .\api-saas
docker compose stop
```

## Melhorias futuras

As ideias abaixo são propostas para versões futuras; não fazem parte da implementação atual:

- **Autenticação e perfis de acesso:** proteger a API e definir quais analistas podem consultar ou solicitar inclusões.
- **Idempotência e confirmação de operações:** evitar duplicidade em novas tentativas após timeout e facilitar a conferência de saldo e auditoria.
- **Testes automatizados e integração contínua:** cobrir tools, grafo e API com respostas simuladas e uma base de teste isolada.
- **Observabilidade:** adicionar logs estruturados, identificador por solicitação e métricas sem registrar chaves ou dados sensíveis.
- **Políticas por plano:** definir com a área responsável se há limites ou permissões diferentes por plano e implementar somente após documentar essas regras.

## Entrega

**Data prevista da entrega:** 30/11/2026  
**Autor:** Carlos Joao Reinert
