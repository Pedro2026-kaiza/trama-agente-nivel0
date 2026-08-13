"""CLI do Nível 0 — Agente Investigativo de Trajetórias Profissionais.

Uso:
    python main.py --input ../  --output parecer.json
    python main.py --input ../ --dry-run          # só extração, sem chamar a API
"""
from __future__ import annotations

import argparse
import json
import sys

from extractor import extrair_evidencias
from pipeline import MODELO_PADRAO, rodar_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Agente Investigativo de Trajetórias Profissionais — Nível 0")
    parser.add_argument("--input", required=True, help="Pasta contendo Shares.csv / Comments.csv / Articles.csv")
    parser.add_argument("--output", default=None, help="Caminho do JSON de saída (padrão: imprime no stdout)")
    parser.add_argument("--modelo", default=MODELO_PADRAO, help=f"Modelo Claude a usar (padrão: {MODELO_PADRAO})")
    parser.add_argument("--max-tokens", type=int, default=16000)
    parser.add_argument("--contexto-vaga", default="", help="Descrição da vaga (opcional), para a seção leitura_vs_contexto_da_vaga")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Roda só a extração de evidências (etapa 1), sem chamar a API. Útil para testar o parsing dos CSVs sem custo.",
    )
    args = parser.parse_args()

    if args.dry_run:
        evidencias = extrair_evidencias(args.input)
        resultado = {"evidencias_extraidas": [e.to_dict() for e in evidencias], "total": len(evidencias)}
    else:
        resultado = rodar_pipeline(
            args.input, modelo=args.modelo, max_tokens=args.max_tokens, contexto_vaga=args.contexto_vaga
        )

    texto_saida = json.dumps(resultado, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(texto_saida)
        print(f"Parecer salvo em {args.output}", file=sys.stderr)
    else:
        print(texto_saida)


if __name__ == "__main__":
    main()
