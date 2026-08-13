"""Checagem de citação (seção 6 do Direcionamento).

Antes de qualquer hipótese chegar ao resultado final, valida em código que todo ID de
evidência citado nela existe de fato na lista retornada pela etapa de extração.
Hipótese com ID inexistente é rejeitada inteira — nunca exibida, mesmo parcialmente.
"""
from dataclasses import dataclass

from extractor import Evidencia


@dataclass
class HipoteseRejeitada:
    id_hipotese: str
    motivo: str
    ids_invalidos: list[str]


def validar_hipoteses(
    hipoteses_brutas: list[dict], evidencias: list[Evidencia]
) -> tuple[list[dict], list[HipoteseRejeitada]]:
    """Retorna (hipóteses aceitas, hipóteses rejeitadas com motivo)."""
    ids_existentes = {e.id for e in evidencias}

    aceitas: list[dict] = []
    rejeitadas: list[HipoteseRejeitada] = []

    for h in hipoteses_brutas:
        citadas = h.get("evidencias_citadas") or []
        if not citadas:
            rejeitadas.append(
                HipoteseRejeitada(
                    id_hipotese=h.get("id_hipotese", "?"),
                    motivo="Hipótese sem nenhuma evidência citada.",
                    ids_invalidos=[],
                )
            )
            continue

        invalidos = [eid for eid in citadas if eid not in ids_existentes]
        if invalidos:
            rejeitadas.append(
                HipoteseRejeitada(
                    id_hipotese=h.get("id_hipotese", "?"),
                    motivo="Cita ID de evidência que não existe na lista extraída (possível alucinação de citação).",
                    ids_invalidos=invalidos,
                )
            )
            continue

        aceitas.append(h)

    return aceitas, rejeitadas
