"""Controle de uso dos códigos de acesso (?codigo=) via planilha Google, através de
um Web App do Google Apps Script — sem credenciais de service account, só uma URL.

A URL fica em GOOGLE_SHEETS_WEBHOOK_URL (.env local / Secrets do Streamlit Cloud).
Se não estiver configurada, o controle fica desativado silenciosamente (não trava
o app rodando local, antes de configurar isso).

Falha aberta de propósito: se a planilha não responder (rede instável, script fora
do ar), assumimos "não usado" em vez de bloquear um testador por uma falha da nossa
ferramenta, não dele. Pelo mesmo motivo, uma falha ao enviar o parecer por e-mail
nunca aparece pra quem está testando — o pior caso é Pedro não receber o e-mail,
não a pessoa ficar travada na tela.
"""
from __future__ import annotations

import json
import os
import urllib.request
from urllib.parse import quote

TIMEOUT_SEGUNDOS = 20  # maior que as outras chamadas: o payload inclui o parecer inteiro


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


def _montar_resumo(resultado: dict) -> str:
    linhas = []
    meta = resultado.get("_meta") or {}
    linhas.append(f"Evidências analisadas: {meta.get('total_evidencias', '?')}")
    linhas.append("")
    linhas.append("CONTEXTO DA ANÁLISE")
    linhas.append(resultado.get("contexto_analise") or "—")
    linhas.append("")
    linhas.append("NARRATIVA PROFISSIONAL")
    linhas.append(resultado.get("narrativa_profissional") or "—")
    linhas.append("")
    linhas.append("HIPÓTESES")
    for h in resultado.get("hipoteses") or []:
        linhas.append(f"- [{h.get('confianca')}] {h.get('descricao')}")
    linhas.append("")
    linhas.append("PERGUNTAS DE ENTREVISTA")
    for q in resultado.get("perguntas_entrevista") or []:
        linhas.append(f"- {q}")
    linhas.append("")
    linhas.append("(Parecer completo em JSON no anexo deste e-mail.)")
    return "\n".join(linhas)


def marcar_codigo_usado(codigo: str, resultado: dict | None = None) -> None:
    """Marca o código como usado na planilha. Se `resultado` (o parecer completo) for
    passado, o Apps Script também envia o parecer por e-mail pra Pedro (anexo JSON +
    resumo legível no corpo)."""
    url = _webhook_url()
    if not url:
        return
    payload: dict = {"codigo": codigo}
    if resultado is not None:
        payload["parecer_json"] = json.dumps(resultado, ensure_ascii=False)
        payload["parecer_resumo"] = _montar_resumo(resultado)
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=TIMEOUT_SEGUNDOS)
    except Exception:
        pass
