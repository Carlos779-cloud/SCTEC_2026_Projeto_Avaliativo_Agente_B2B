"""Exporta o grafo compilado do agente para Mermaid e PNG."""

import argparse
from pathlib import Path

from langchain_core.runnables.graph import MermaidDrawMethod

from agent.graph import agent_graph


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gera uma visualização do StateGraph do agente SaaS."
    )
    parser.add_argument(
        "--mermaid-only",
        action="store_true",
        help="Gera apenas os arquivos Mermaid, sem chamar o renderizador PNG remoto.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Pasta para salvar graph-etapa5.mmd, graph-etapa5.md e graph-etapa5.png.",
    )
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    drawable_graph = agent_graph.get_graph()
    mermaid_source = drawable_graph.draw_mermaid()

    mermaid_path = output_dir / "graph-etapa5.mmd"
    markdown_path = output_dir / "graph-etapa5.md"
    mermaid_path.write_text(mermaid_source + "\n", encoding="utf-8")
    markdown_path.write_text(
        "# Fluxo do agente SaaS\n\n```mermaid\n"
        + mermaid_source
        + "\n```\n",
        encoding="utf-8",
    )

    print(f"Fonte Mermaid salva em: {mermaid_path}")
    print(f"Markdown salvo em: {markdown_path}")

    if args.mermaid_only:
        return 0

    png_path = output_dir / "graph-etapa5.png"
    try:
        drawable_graph.draw_mermaid_png(
            output_file_path=str(png_path),
            draw_method=MermaidDrawMethod.API,
            max_retries=1,
        )
    except Exception:
        print(
            "Não foi possível renderizar o PNG. Os arquivos Mermaid foram salvos; "
            "use --mermaid-only para gerar sem acesso ao renderizador remoto."
        )
        return 1

    print(f"Imagem PNG salva em: {png_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
