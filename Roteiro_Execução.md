# Guia de execução e cenários

Guia para clonar o projeto, iniciar o SaaS e o agente e enviar seis solicitações de exemplo.

## Pré-requisitos

- Python 3.12 ou superior, [uv](https://docs.astral.sh/uv/) e Git.
- Docker Engine e Docker Compose v2.
- Chave Groq válida em `saas-agent/.env`.
- Bash no Linux ou PowerShell no Windows.

Não mostre nem compartilhe `.env` ou a chave Groq.

## Clonar e configurar

Substitua o marcador pelo endereço do repositório:

```bash
git clone <LINK_DO_GIT_CLONE>
cd SCTEC_2026_Projeto_Avaliativo_Agente_B2B
```

Windows PowerShell, a partir da raiz do clone:

```powershell
cd .\saas-agent
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
uv lock --check
uv sync --locked
uv run python --version
```

Linux Bash, a partir da raiz do clone:

```bash
cd saas-agent
test -f .env || cp .env.example .env
nano .env
uv lock --check
uv sync --locked
uv run python --version
```

Preencha `GROQ_API_KEY` em `.env` antes de iniciar o agente.

## Iniciar os serviços

Use dois terminais. No primeiro, inicie o SaaS a partir da raiz.

PowerShell:

```powershell
cd .\api-saas
uv sync
docker compose up -d --build
dokcer compose up -
docker ps
Invoke-RestMethod -Uri http://localhost:8002/health
```

Linux Bash:

```bash
cd api-saas
docker compose up -d --build
dokcer compose up -
docker ps
curl --fail http://localhost:8002/health
```

No segundo terminal, também a partir da raiz, inicie o agente:

```bash
cd saas-agent
uv run uvicorn api.server:app --host 127.0.0.1 --port 8001
```

Swagger SaaS: `http://localhost:8002/docs`. Swagger do agente: `http://127.0.0.1:8001/docs`. A rota para os cenários é `POST /consultar`.

## Conferir o saldo antes do cenário 1

A inclusão válida altera saldo e auditoria. Em uma base nova, a assinatura 10 começa com 1.200 créditos. Confira antes:

PowerShell: `Invoke-RestMethod -Uri http://localhost:8002/assinaturas/1 | Select-Object id,status,saldo_creditos_api`

Linux: `curl --fail http://localhost:8002/assinaturas/1`

A base local usada anteriormente já chegou a 2.700 créditos na assinatura 10. Não repita o cenário nominal nessa base sem querer alterar o saldo. Os outros cinco cenários não devem incluir créditos.

## Enviar solicitações

Defina esta função no PowerShell:

```powershell
function Enviar-Cenario {
    param([Parameter(Mandatory)][string]$Mensagem)
    $payload = @{ mensagem = $Mensagem } | ConvertTo-Json -Compress
    $body = [System.Text.Encoding]::UTF8.GetBytes($payload)
    Invoke-RestMethod -Uri http://127.0.0.1:8001/consultar -Method Post -ContentType 'application/json; charset=utf-8' -Body $body
}
```

Defina esta função no Bash:

```bash
enviar_cenario() {
  local body
  body=$(python3 -c 'import json,sys; print(json.dumps({"mensagem":sys.argv[1]}, ensure_ascii=False))' "$1")
  curl --fail-with-body http://127.0.0.1:8001/consultar \
    -H 'Content-Type: application/json' --data-binary "$body"
}
```

Rode uma mensagem por vez. Em cada chamada Bash, substitua `Enviar-Cenario` por `enviar_cenario`.

## Seis cenários

### 1. Inclusão válida — altera saldo

`Inclua 1500 créditos extras para a empresa Logística Sul. Motivo: teste de demonstração aprovado pelo analista.`

Esperado: `parecer: aprovado`, confirmação do SaaS e saldo atualizado. Use base preparada e execute uma vez.

### 2. Empresa ambígua — pede escolha

`Consulte a assinatura da empresa Alpha.`

Esperado: recusa com opções compatíveis; nenhuma inclusão.

### 3. Quantidade acima do limite — bloqueia antes do POST

`Inclua 5000 créditos extras para a empresa Logística Sul. Motivo: teste de validação do limite.`

Esperado: `motivo_recusa: quantidade_invalida`; sem POST e sem mudança de saldo.

### 4. Empresa inexistente — encerra a busca

`Consulte a assinatura da empresa Empresa Ceramifix.`

Esperado: `motivo_recusa: empresa_nao_encontrada`; sem consulta de assinatura ou inclusão.

### 5. Assinatura inativa — bloqueia a inclusão

A massa inicial contém TechFlow Soluções com status `INATIVA`.

`Inclua 100 créditos extras para a empresa TechFlow Soluções. Motivo: teste de bloqueio de assinatura inativa.`

Esperado: `motivo_recusa: assinatura_inativa`; sem POST e sem mudança de saldo.

### 6. Fora de escopo — recusa cancelamento

`Cancele a assinatura da empresa Logística Sul.`

Esperado: `motivo_recusa: solicitacao_fora_do_escopo`; nenhuma ferramenta de alteração chamada.

## Comandos para enviar os cenários

PowerShell:

```powershell
Enviar-Cenario 'Inclua 1500 créditos extras para a empresa Logística Sul. Motivo: teste de demonstração aprovado pelo analista.'
Enviar-Cenario 'Consulte a assinatura da empresa Alpha.'
Enviar-Cenario 'Inclua 5000 créditos extras para a empresa Logística Sul. Motivo: teste de validação do limite.'
Enviar-Cenario 'Consulte a assinatura da empresa Empresa Inexistente 999.'
Enviar-Cenario 'Inclua 100 créditos extras para a empresa TechFlow Soluções. Motivo: teste de bloqueio de assinatura inativa.'
Enviar-Cenario 'Cancele a assinatura da empresa Logística Sul.'
```

Linux Bash:

```bash
enviar_cenario 'Inclua 1500 créditos extras para a empresa Logística Sul. Motivo: teste de demonstração aprovado pelo analista.'
enviar_cenario 'Consulte a assinatura da empresa Alpha.'
enviar_cenario 'Inclua 5000 créditos extras para a empresa Logística Sul. Motivo: teste de validação do limite.'
enviar_cenario 'Consulte a assinatura da empresa Empresa Inexistente 999.'
enviar_cenario 'Inclua 100 créditos extras para a empresa TechFlow Soluções. Motivo: teste de bloqueio de assinatura inativa.'
enviar_cenario 'Cancele a assinatura da empresa Logística Sul.'
```

## Parar os serviços

Pare o agente com `Ctrl+C`. Para parar os containers preservando o volume:

```bash
cd api-saas
docker compose stop
```

`docker compose down -v` apaga o volume e os dados locais; use só se quiser recriar a base.
