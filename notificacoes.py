"""Notificação simples via ntfy.sh quando uma análise é concluída.

O nome do canal fica em NTFY_TOPIC (.env local / Secrets do Streamlit Cloud).
Se não estiver configurado, a notificação é pulada silenciosamente — não deve
nunca travar o fluxo do usuário por causa de um aviso que é só pra Pedro.
"""
from __future__ import annotations

import os
import urllib.request

TIMEOUT_SEGUNDOS = 8


def notificar_conclusao(codigo: str, nivel: str) -> None:
    topico = os.environ.get("NTFY_TOPIC")
    if not topico:
        return
    mensagem = f"Análise concluída — código {codigo} (nível {nivel})"
    try:
        req = urllib.request.Request(
            f"https://ntfy.sh/{topico}",
            data=mensagem.encode("utf-8"),
            headers={"Title": "TRAMA Nível 0 - nova análise concluída"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=TIMEOUT_SEGUNDOS)
    except Exception:
        pass
