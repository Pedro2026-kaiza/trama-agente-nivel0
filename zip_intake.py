"""Extração segura do .zip completo da exportação de dados do LinkedIn.

Allowlist rígida: só os arquivos abaixo saem do zip. Tudo mais (messages.csv,
PhoneNumbers.csv, Email Addresses.csv, Connections.csv, Invitations.csv,
Ad_Targeting.csv, Receipts_v2.csv, Registration.csv, Job Applications, e
qualquer coisa fora da lista) é ignorado sem nunca ser lido — o código só olha
o nome de cada entrada do zip antes de decidir extrair ou pular; conteúdo de
arquivo não permitido nunca é aberto.

Guarda também contra zip-slip (entradas com path traversal) e contra arquivos
anormalmente grandes.

NOTA: Recommendations_Received.csv (recomendações recebidas de terceiros) foi
incluído por decisão explícita do usuário (confirmada em conversa), mesmo o
Direcionamento_Nivel_0 e o documento MVP originalmente marcando "depoimentos
de terceiros" como pendente de resolução de consentimento (seção 2 do
Direcionamento, seção 3 do MVP) — a leitura aceita foi que é um recurso nativo
e opt-in do próprio LinkedIn (quem recomenda escolhe publicar). Ver
extractor.py:_extrair_recommendations para como essas evidências são marcadas
como de origem de terceiro no campo "contexto".
"""
from __future__ import annotations

import zipfile
from pathlib import Path, PurePosixPath

CSV_PERMITIDOS = {
    "positions.csv",
    "projects.csv",
    "skills.csv",
    "education.csv",
    "certifications.csv",
    "shares.csv",
    "comments.csv",
    "rich_media.csv",
    "recommendations_received.csv",
}

TAMANHO_MAX_POR_ARQUIVO = 100 * 1024 * 1024  # 100 MB
TAMANHO_MAX_TOTAL = 300 * 1024 * 1024  # 300 MB


def _classificar_entrada(nome_no_zip: str) -> tuple[bool, str]:
    """Decide se uma entrada do zip é permitida, sem ler seu conteúdo.

    Retorna (permitido, caminho_relativo_de_destino).
    """
    partes = PurePosixPath(nome_no_zip.replace("\\", "/")).parts
    if not partes:
        return False, ""

    basename_lower = partes[-1].lower()

    if basename_lower in CSV_PERMITIDOS:
        return True, partes[-1]  # achatado direto na raiz da pasta de destino

    if len(partes) >= 2 and partes[-2].lower() == "articles" and basename_lower.endswith(".html"):
        return True, f"Articles/{partes[-1]}"

    return False, ""


def extrair_zip_permitido(arquivo_zip, pasta_destino: Path) -> list[str]:
    """Extrai só os membros da allowlist do .zip para pasta_destino.

    arquivo_zip: caminho (str/Path) ou objeto file-like (ex.: io.BytesIO) aceito
    por zipfile.ZipFile.

    Levanta ValueError se o zip não puder ser aberto, tiver uma entrada com
    path traversal, ou passar dos limites de tamanho.

    Retorna a lista de caminhos relativos efetivamente extraídos.
    """
    pasta_destino = Path(pasta_destino).resolve()
    extraidos: list[str] = []
    tamanho_total = 0

    try:
        zf = zipfile.ZipFile(arquivo_zip)
    except zipfile.BadZipFile as e:
        raise ValueError(f"Arquivo enviado não é um .zip válido: {e}") from e

    with zf:
        for info in zf.infolist():
            if info.is_dir():
                continue

            permitido, destino_relativo = _classificar_entrada(info.filename)
            if not permitido:
                continue  # nunca lido, nunca escrito em disco

            if info.file_size > TAMANHO_MAX_POR_ARQUIVO:
                raise ValueError(f"Arquivo '{info.filename}' excede o tamanho máximo permitido por arquivo.")
            tamanho_total += info.file_size
            if tamanho_total > TAMANHO_MAX_TOTAL:
                raise ValueError("Tamanho total dos arquivos permitidos no .zip excede o limite permitido.")

            destino = (pasta_destino / destino_relativo).resolve()
            if destino != pasta_destino and pasta_destino not in destino.parents:
                # zip-slip: entrada tenta escapar da pasta de destino (ex.: "../../etc/passwd")
                raise ValueError(f"Entrada de zip suspeita (path traversal): {info.filename}")

            destino.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as origem, open(destino, "wb") as saida:
                saida.write(origem.read())
            extraidos.append(destino_relativo)

    return extraidos
