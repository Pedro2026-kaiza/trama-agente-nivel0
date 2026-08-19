"""Códigos de acesso dos "links filhos" da experiência com os 15 profissionais de RH
(?codigo=J3 na URL). Controla só o gate de acesso (código válido + 1 uso por link,
ver codigo_tracking.py) — não pré-preenche mais contexto de vaga: decisão explícita
de deixar aberto para qualquer perfil, sem direcionar pra um texto fictício.

Os grupos J/M/S continuam existindo só como identificação de qual lote de convite
foi entregue a cada pessoa (útil pra Pedro rastrear quem é quem), sem efeito no
comportamento do app.
"""

GRUPOS = {
    "J": "Júnior",
    "M": "Pleno/Middle",
    "S": "Sênior",
    "T": "Teste interno (Pedro)",
    # Uso pessoal do Pedro (não é um dos 15 testadores) — igual ao T1, nunca tem
    # linha correspondente na planilha, então codigo_ja_usado() sempre volta False:
    # dá pra rodar quantas análises quiser, à vontade, sem "gastar" nada.
    "P": "Uso pessoal (Pedro)",
}

CODIGOS_VALIDOS = [f"{letra}{numero}" for letra in "JMSP" for numero in range(1, 6)] + ["T1"]


def grupo_do_codigo(codigo: str) -> str | None:
    """Retorna o nome do grupo (ex.: "Júnior") para um código válido, ou None."""
    codigo = (codigo or "").strip().upper()
    if codigo not in CODIGOS_VALIDOS:
        return None
    return GRUPOS[codigo[0]]
