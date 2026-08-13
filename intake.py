"""Ponto de entrada via .zip completo da exportação de dados do LinkedIn.

Extrai só os arquivos permitidos (zip_intake.py) para uma pasta temporária,
roda a extração de evidências (extractor.py) e apaga a pasta temporária
inteira ao final — com sucesso ou com erro. Nada do .zip enviado ou dos
arquivos extraídos sobrevive em disco depois desta função retornar.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from extractor import Evidencia, extrair_contexto_nao_citavel, extrair_evidencias
from zip_intake import extrair_zip_permitido


def processar_zip_linkedin(arquivo_zip) -> tuple[list[Evidencia], str]:
    """Recebe um .zip (caminho ou objeto file-like) e retorna (evidências, contexto_nao_citavel).

    A pasta temporária de trabalho é sempre apagada antes do retorno, mesmo se
    a extração falhar no meio do caminho (tempfile.TemporaryDirectory garante
    isso via __exit__, inclusive em caminho de exceção).
    """
    with tempfile.TemporaryDirectory() as tmp:
        pasta = Path(tmp)
        extrair_zip_permitido(arquivo_zip, pasta)
        evidencias = extrair_evidencias(pasta)
        contexto_nao_citavel = extrair_contexto_nao_citavel(pasta)
    return evidencias, contexto_nao_citavel
