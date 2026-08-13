"""Orquestração do Nível 0: extração -> chamada única de raciocínio -> checagem de
citação -> cálculo determinístico de confiança -> parecer final.

Sem banco de dados, sem interface, sem autenticação de usuário — só a chave de API
da Anthropic, lida de variável de ambiente.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from confidence import calcular_confianca
from extractor import Evidencia, extrair_contexto_nao_citavel, extrair_evidencias
from master_prompt import MASTER_PROMPT, montar_mensagem_usuario
from validation import validar_hipoteses

MODELO_PADRAO = "claude-opus-5"

# Carrega .env da pasta do projeto (se existir) para dentro de os.environ.
# Não sobrescreve uma ANTHROPIC_API_KEY já definida no ambiente do sistema.
load_dotenv(Path(__file__).resolve().parent / ".env")


def _chamar_modelo(
    evidencias: list[Evidencia],
    modelo: str,
    max_tokens: int,
    contexto_nao_citavel: str,
    contexto_vaga: str,
) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY não definida. Preencha o arquivo .env na raiz do projeto "
            "(ANTHROPIC_API_KEY=sk-ant-...) ou defina a variável de ambiente antes de rodar o pipeline completo."
        )

    client = anthropic.Anthropic(api_key=api_key)
    resposta = client.messages.create(
        model=modelo,
        max_tokens=max_tokens,
        system=MASTER_PROMPT,
        messages=[{"role": "user", "content": montar_mensagem_usuario(evidencias, contexto_nao_citavel, contexto_vaga)}],
    )
    texto = "".join(bloco.text for bloco in resposta.content if bloco.type == "text")

    if resposta.stop_reason == "max_tokens":
        raise RuntimeError(
            f"Resposta cortada por atingir max_tokens ({max_tokens}) antes de terminar o parecer. "
            "Rode de novo com --max-tokens maior (ex.: --max-tokens 16000)."
        )

    return _extrair_json(texto)


def _extrair_json(texto: str) -> dict:
    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.split("```", 2)[1]
        if texto.startswith("json"):
            texto = texto[4:]
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fim == -1:
        raise ValueError(f"Resposta do modelo não contém um JSON reconhecível:\n{texto[:500]}")
    return json.loads(texto[inicio : fim + 1])


def montar_parecer(
    evidencias: list[Evidencia],
    modelo: str = MODELO_PADRAO,
    max_tokens: int = 16000,
    contexto_nao_citavel: str = "",
    contexto_vaga: str = "",
) -> dict:
    """Etapa 2 em diante: chamada única de raciocínio -> checagem de citação -> confiança.

    Separada de rodar_pipeline() para que quem chama (CLI, UI) possa reportar o
    progresso da extração (rápida, sem rede) separado da chamada ao modelo (lenta).
    """
    evidencias_por_id = {e.id: e for e in evidencias}

    bruto = _chamar_modelo(evidencias, modelo, max_tokens, contexto_nao_citavel, contexto_vaga)

    hipoteses_brutas = bruto.get("hipoteses") or []
    aceitas, rejeitadas = validar_hipoteses(hipoteses_brutas, evidencias)

    hipoteses_finais = []
    for h in aceitas:
        confianca = calcular_confianca(
            evidencia_ids_validados=h["evidencias_citadas"],
            evidencias_por_id=evidencias_por_id,
            contradicao_entre_evidencias=bool(h.get("contradicao_entre_evidencias_citadas", False)),
        )
        hipoteses_finais.append({**h, "confianca": confianca})

    return {
        "evidencias_extraidas": [e.to_dict() for e in evidencias],
        "contexto_analise": bruto.get("contexto_analise"),
        "evidencias_observadas": bruto.get("evidencias_observadas"),
        "padroes_emergentes": bruto.get("padroes_emergentes"),
        "narrativa_profissional": bruto.get("narrativa_profissional"),
        "forcas_evidenciadas": bruto.get("forcas_evidenciadas"),
        "tensoes_e_lacunas": bruto.get("tensoes_e_lacunas"),
        "hipoteses": hipoteses_finais,
        "hipoteses_rejeitadas_por_citacao_invalida": [
            {"id_hipotese": r.id_hipotese, "motivo": r.motivo, "ids_invalidos": r.ids_invalidos}
            for r in rejeitadas
        ],
        "perguntas_entrevista": bruto.get("perguntas_entrevista"),
        "limitacoes_da_analise": bruto.get("limitacoes_da_analise"),
        "leitura_vs_contexto_da_vaga": bruto.get("leitura_vs_contexto_da_vaga"),
        "_meta": {"modelo": modelo, "total_evidencias": len(evidencias)},
    }


def rodar_pipeline(
    pasta_entrada: str | Path,
    modelo: str = MODELO_PADRAO,
    max_tokens: int = 16000,
    contexto_vaga: str = "",
) -> dict:
    evidencias = extrair_evidencias(pasta_entrada)
    contexto_nao_citavel = extrair_contexto_nao_citavel(pasta_entrada)
    return montar_parecer(
        evidencias,
        modelo=modelo,
        max_tokens=max_tokens,
        contexto_nao_citavel=contexto_nao_citavel,
        contexto_vaga=contexto_vaga,
    )
