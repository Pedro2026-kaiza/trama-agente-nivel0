"""Renderização do parecer.json como PDF — camada de apresentação por cima do
JSON, que continua sendo a fonte de verdade (este módulo só lê, nunca recalcula
nem reinterpreta nada do parecer).

Usa Jinja2 pro template (templates/parecer.html) e xhtml2pdf pra converter em
PDF. Escolha em vez de weasyprint: weasyprint precisa de bibliotecas nativas do
GTK3 (libgobject, pango) que não instalam via pip no Windows — xhtml2pdf instala
100% via pip, sem dependência de sistema. Se este pipeline um dia rodar num
servidor Linux, weasyprint voltaria a ser uma opção viável ali.
"""
from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa

_DIR_TEMPLATES = Path(__file__).resolve().parent / "templates"


def _preparar_contexto(resultado: dict) -> dict:
    evidencias_por_id = {e["id"]: e for e in resultado.get("evidencias_extraidas") or []}
    hipoteses = resultado.get("hipoteses") or []
    ids_relevantes = sorted({eid for h in hipoteses for eid in h.get("evidencias_citadas", [])})
    evidencias_relevantes = [evidencias_por_id[eid] for eid in ids_relevantes if eid in evidencias_por_id]

    return {
        "resultado": resultado,
        "meta": resultado.get("_meta") or {},
        "evidencias_relevantes": evidencias_relevantes,
        "hipoteses": hipoteses,
        "hipoteses_rejeitadas": resultado.get("hipoteses_rejeitadas_por_citacao_invalida") or [],
        "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }


def _renderizar_html(resultado: dict) -> str:
    env = Environment(loader=FileSystemLoader(str(_DIR_TEMPLATES)))
    template = env.get_template("parecer.html")
    return template.render(**_preparar_contexto(resultado))


def gerar_pdf_bytes(resultado: dict) -> bytes:
    """Renderiza o parecer como PDF e retorna os bytes, sem escrever em disco —
    usado pelo app.py pra oferecer download direto no navegador (st.download_button)."""
    html = _renderizar_html(resultado)
    buffer = io.BytesIO()
    status = pisa.CreatePDF(html, dest=buffer, encoding="utf-8")

    if status.err:
        raise RuntimeError(
            f"Falha ao gerar PDF ({status.err} erro(s) reportado(s) pelo xhtml2pdf — "
            "ver mensagens de log acima para detalhes)."
        )

    return buffer.getvalue()


def gerar_pdf(resultado: dict, caminho_saida: str | Path) -> Path:
    """Renderiza o parecer (mesmo dict que sai de pipeline.montar_parecer / o
    conteúdo de um parecer.json já salvo) como PDF em caminho_saida (CLI)."""
    dados = gerar_pdf_bytes(resultado)

    caminho_saida = Path(caminho_saida)
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    caminho_saida.write_bytes(dados)

    return caminho_saida
