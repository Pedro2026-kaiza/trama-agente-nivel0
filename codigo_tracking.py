"""Controle de uso dos códigos de acesso (?codigo=) via planilha Google, através de
um Web App do Google Apps Script — sem credenciais de service account, só uma URL.

A URL fica em GOOGLE_SHEETS_WEBHOOK_URL (.env local / Secrets do Streamlit Cloud).
Se não estiver configurada, o controle fica desativado silenciosamente (não trava
o app rodando local, antes de configurar isso).

Falha aberta de propósito: se a planilha não responder (rede instável, script fora
do ar), assumimos "não usado" em vez de bloquear um testador por uma falha da nossa
ferramenta, não dele.
"""
from __future__ import annotations

import json
import os
import urllib.request
from urllib.parse import quote

TIMEOUT_SEGUNDOS = 8


def _webhook_url() -> str | None:
    return os.environ.get("GOOGLE_SHEETS_WEBHOOK_URL") or None


def codigo_ja_usado(codigo: str) -> bool:
    url = _webhook_url()
    if not url:
        return False
    try:
        with urllib.request.urlopen(f"{url}?codigo={quote(codigo)}", timeout=TIMEOUT_SEGUNDOS) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
        return bool(dados.get("usado"))
    except Exception:
        return False


def marcar_codigo_usado(codigo: str) -> None:
    url = _webhook_url()
    if not url:
        return
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps({"codigo": codigo}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=TIMEOUT_SEGUNDOS)
    except Exception:
        pass
