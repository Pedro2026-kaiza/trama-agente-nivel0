"""Gera um PDF a partir de um parecer.json já existente, sem precisar rodar o
pipeline (sem chamada à API) — útil pra reformatar um parecer já gerado, ou pra
gerar o PDF de resultados salvos anteriormente.

Uso:
    python gerar_pdf.py --input parecer.json --output parecer.pdf
"""
from __future__ import annotations

import argparse
import json

from pdf_export import gerar_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description="Converte um parecer.json em PDF")
    parser.add_argument("--input", required=True, help="Caminho do parecer.json de entrada")
    parser.add_argument("--output", required=True, help="Caminho do .pdf de saída")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        resultado = json.load(f)

    caminho = gerar_pdf(resultado, args.output)
    print(f"PDF gerado em {caminho}")


if __name__ == "__main__":
    main()
