"""Lista os IDs de modelos disponibilizados pela API Groq para esta chave."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq


def main() -> int:
    env_file = Path(__file__).resolve().with_name(".env")
    load_dotenv(dotenv_path=env_file)

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print(
            "GROQ_API_KEY não encontrada. Configure-a em saas-agent/.env "
            "ou no ambiente antes de executar este script.",
            file=sys.stderr,
        )
        return 1

    try:
        client = Groq(api_key=api_key)
        models = client.models.list()
    except Exception as exc:
        print(
            f"Não foi possível consultar os modelos Groq ({type(exc).__name__}). "
            "Confira a chave, a conexão e as permissões da conta.",
            file=sys.stderr,
        )
        return 1

    model_ids = sorted(model.id for model in models.data)
    if not model_ids:
        print("A API Groq não retornou modelos para esta chave.")
        return 0

    print("IDs de modelos retornados pela API Groq:")
    for model_id in model_ids:
        print(model_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# Acessa a pasta do projeto SaaS Agent.
# cd saas-agent

# Lista os modelos disponíveis na API Groq para a chave configurada.
# python listar_modelos.py
 