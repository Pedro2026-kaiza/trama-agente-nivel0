"""Cálculo determinístico de confiança por hipótese (seção 5 do Direcionamento).

Nunca chamado no prompt do modelo — o grau de confiança é sempre calculado aqui,
em código, a partir da própria lista de evidências extraída na etapa 1.

Regra:
  3+ evidências, de 2+ fontes distintas, sem contradição entre elas -> "Alta"
  1-2 evidências, ou evidências de uma única fonte                  -> "Média"
  Sem evidência direta suficiente (0 evidências válidas)            -> None (vira lacuna, não hipótese)
"""
from extractor import Evidencia

CONFIANCA_ALTA = "Alta"
CONFIANCA_MEDIA = "Média"


def calcular_confianca(
    evidencia_ids_validados: list[str],
    evidencias_por_id: dict[str, Evidencia],
    contradicao_entre_evidencias: bool,
) -> str | None:
    """Recebe apenas IDs já validados (existentes de fato na extração) — ver validation.py."""
    n = len(evidencia_ids_validados)
    if n == 0:
        return None

    fontes_distintas = {evidencias_por_id[eid].fonte for eid in evidencia_ids_validados}

    if n >= 3 and len(fontes_distintas) >= 2 and not contradicao_entre_evidencias:
        return CONFIANCA_ALTA
    return CONFIANCA_MEDIA
