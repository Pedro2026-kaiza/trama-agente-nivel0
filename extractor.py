"""Extração determinística de evidências a partir dos CSVs de exportação do LinkedIn.

Sem chamada a modelo nesta etapa (Nível 0, item 1 do Direcionamento).
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from pathlib import Path

# Vocabulário mínimo para classificação temática determinística por palavra-chave.
# Não é uma taxonomia definitiva — é um ponto de partida legível e fácil de ajustar.
# Sem correspondência -> "Geral" (o agente de raciocínio identifica padrões mais finos depois).
TEMA_KEYWORDS: dict[str, list[str]] = {
    "Produto": ["produto", "funcionalidade", "feature", "adoção", "usuário", "roadmap"],
    "Dados e Decisão": ["dado", "dados", "dashboard", "métrica", "decisão", "decisões"],
    "Liderança e Mentoria": ["mentoria", "mentor", "liderei", "liderar", "time", "equipe"],
    "Estratégia e Ecossistema": ["ecossistema", "estratégia", "mercado", "polvo"],
    "Finanças e Crédito": ["crédito", "scoring", "inadimplência", "reinvestimento", "financeiro", "financeira", "pagamento"],
    "Tecnologia": ["tecnologia", "sistema", "sistemas", "software", "tech"],
    "Empreendedorismo": ["empreender", "empreendedor", "microempreendedor", "negócio próprio"],
}


@dataclass
class Evidencia:
    id: str
    fonte: str
    trecho: str
    contexto: str
    data: str
    tema: str

    def to_dict(self) -> dict:
        return asdict(self)


def _classificar_tema(texto: str) -> str:
    texto_lower = texto.lower()
    for tema, palavras in TEMA_KEYWORDS.items():
        if any(re.search(rf"\b{re.escape(p)}", texto_lower) for p in palavras):
            return tema
    return "Geral"


def _ler_csv(caminho: Path) -> list[dict[str, str]]:
    with caminho.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _col(row: dict[str, str], *candidatos: str) -> str:
    """Busca o valor de uma coluna tolerando variações de nome (case-insensitive)."""
    lower_map = {k.lower().strip(): v for k, v in row.items()}
    for nome in candidatos:
        if nome.lower() in lower_map and lower_map[nome.lower()].strip():
            return lower_map[nome.lower()].strip()
    return ""


def _extrair_shares(caminho: Path) -> list[dict]:
    brutos = []
    for row in _ler_csv(caminho):
        trecho = _col(row, "ShareCommentary", "Commentary", "Comment")
        if not trecho:
            continue
        link = _col(row, "ShareLink", "Link")
        visibilidade = _col(row, "Visibility")
        brutos.append(
            dict(
                fonte="LinkedIn - Post",
                trecho=trecho,
                contexto=f"Post próprio no LinkedIn. Link: {link or 'não informado'}. Visibilidade: {visibilidade or 'não informada'}.",
                data=_col(row, "Date"),
            )
        )
    return brutos


def _extrair_comments(caminho: Path) -> list[dict]:
    brutos = []
    for row in _ler_csv(caminho):
        trecho = _col(row, "Message")
        if not trecho:
            continue
        link = _col(row, "Link")
        brutos.append(
            dict(
                fonte="LinkedIn - Comentário",
                trecho=trecho,
                contexto=f"Comentário feito em post de terceiros. Link do post comentado: {link or 'não informado'}. "
                         f"Nota: exportação nativa do LinkedIn só traz comentários feitos pelo próprio usuário, não recebidos.",
                data=_col(row, "Date"),
            )
        )
    return brutos


def _extrair_articles(caminho: Path) -> list[dict]:
    """Formato do dado fictício de teste: Articles.csv com Title/Link/Date.

    A exportação real do LinkedIn traz artigos como arquivos .html individuais
    dentro de uma pasta Articles/ — ver _extrair_articles_html().
    """
    brutos = []
    for row in _ler_csv(caminho):
        titulo = _col(row, "Title")
        if not titulo:
            continue
        link = _col(row, "Link")
        brutos.append(
            dict(
                fonte="LinkedIn - Artigo",
                trecho=titulo,
                contexto=f"Artigo publicado no LinkedIn. Link: {link or 'não informado'}.",
                data=_col(row, "Date"),
            )
        )
    return brutos


def _extrair_positions(caminho: Path) -> list[dict]:
    brutos = []
    for row in _ler_csv(caminho):
        empresa = _col(row, "Company Name", "CompanyName", "Company")
        cargo = _col(row, "Title")
        if not empresa and not cargo:
            continue
        descricao = _col(row, "Description")
        local = _col(row, "Location")
        inicio = _col(row, "Started On", "StartedOn", "Start Date")
        fim = _col(row, "Finished On", "FinishedOn", "End Date")
        brutos.append(
            dict(
                fonte="LinkedIn - Cargo",
                trecho=descricao or f"{cargo} — {empresa}".strip(" —"),
                contexto=f"Cargo registrado no LinkedIn: {cargo or 'não informado'} em {empresa or 'não informado'}"
                         f"{f', {local}' if local else ''}. Período: {inicio or '?'} – {fim or 'atual'}.",
                data=inicio,
            )
        )
    return brutos


def _extrair_projects(caminho: Path) -> list[dict]:
    brutos = []
    for row in _ler_csv(caminho):
        titulo = _col(row, "Title")
        descricao = _col(row, "Description")
        if not titulo and not descricao:
            continue
        url = _col(row, "Url", "Link")
        inicio = _col(row, "Started On", "StartedOn")
        fim = _col(row, "Finished On", "FinishedOn")
        brutos.append(
            dict(
                fonte="LinkedIn - Projeto",
                trecho=descricao or titulo,
                contexto=f"Projeto registrado no LinkedIn. Link: {url or 'não informado'}. "
                         f"Período: {inicio or '?'} – {fim or 'em andamento'}.",
                data=inicio,
            )
        )
    return brutos


def _extrair_recommendations(caminho: Path) -> list[dict]:
    """Recomendações recebidas — texto escrito por terceiros, não pelo candidato.

    Incluída na allowlist por decisão explícita do usuário (recurso nativo e
    opt-in do LinkedIn: quem recomenda escolhe publicar). O campo "contexto"
    marca claramente a origem de terceiro, para que fique visível em qualquer
    hipótese que cite essa evidência — nunca escondemos a origem.
    """
    brutos = []
    for row in _ler_csv(caminho):
        texto = _col(row, "Text")
        if not texto:
            continue
        status = _col(row, "Status")
        if status and "revoke" in status.lower():
            continue  # recomendação revogada pelo autor — não deveria circular como evidência
        nome = f"{_col(row, 'First Name')} {_col(row, 'Last Name')}".strip()
        cargo = _col(row, "Job Title")
        empresa = _col(row, "Company")
        origem = nome or "pessoa não identificada"
        if cargo or empresa:
            origem += f" ({cargo}{' na ' + empresa if empresa else ''})".replace("  ", " ")
        brutos.append(
            dict(
                fonte="LinkedIn - Recomendação recebida (terceiro)",
                trecho=texto,
                contexto=f"Recomendação recebida no LinkedIn, ESCRITA POR TERCEIRO: {origem}. "
                         f"Não é autodeclaração do candidato — tratar como relato de outra pessoa.",
                data=_col(row, "Creation Date", "CreationDate"),
            )
        )
    return brutos


def _extrair_education(caminho: Path) -> list[dict]:
    brutos = []
    for row in _ler_csv(caminho):
        escola = _col(row, "School Name", "SchoolName")
        grau = _col(row, "Degree Name", "DegreeName")
        if not escola and not grau:
            continue
        notas = _col(row, "Notes")
        atividades = _col(row, "Activities")
        inicio = _col(row, "Start Date", "StartDate")
        fim = _col(row, "End Date", "EndDate")
        brutos.append(
            dict(
                fonte="LinkedIn - Formação",
                trecho=notas or atividades or f"{grau} — {escola}".strip(" —"),
                contexto=f"Formação registrada no LinkedIn: {grau or 'não informado'}, {escola or 'não informado'}. "
                         f"Período: {inicio or '?'} – {fim or 'atual'}.",
                data=inicio,
            )
        )
    return brutos


def _extrair_certifications(caminho: Path) -> list[dict]:
    brutos = []
    for row in _ler_csv(caminho):
        nome = _col(row, "Name")
        if not nome:
            continue
        autoridade = _col(row, "Authority")
        url = _col(row, "Url", "Link")
        inicio = _col(row, "Started On", "StartedOn")
        brutos.append(
            dict(
                fonte="LinkedIn - Certificado",
                trecho=nome,
                contexto=f"Certificado registrado no LinkedIn, emitido por {autoridade or 'não informado'}. "
                         f"Link: {url or 'não informado'}.",
                data=inicio,
            )
        )
    return brutos


def _extrair_rich_media(caminho: Path) -> list[dict]:
    """Schema exato deste arquivo varia entre exportações; leitura tolerante por candidatos."""
    brutos = []
    for row in _ler_csv(caminho):
        titulo = _col(row, "Title", "Media Title", "Article Title")
        descricao = _col(row, "Description", "Caption")
        trecho = descricao or titulo
        if not trecho:
            continue
        link = _col(row, "Media Link", "Original Link", "LinkedIn Link", "Link", "Url")
        data = _col(row, "Date", "Created Date", "Published Date")
        brutos.append(
            dict(
                fonte="LinkedIn - Mídia",
                trecho=trecho,
                contexto=f"Mídia associada ao perfil do LinkedIn. Link: {link or 'não informado'}.",
                data=data,
            )
        )
    return brutos


class _ExtratorTextoHTML(HTMLParser):
    """Extrai <title> e texto visível de um HTML, sem dependências externas."""

    def __init__(self):
        super().__init__()
        self._partes_corpo: list[str] = []
        self._partes_titulo: list[str] = []
        self._em_titulo = False
        self._em_ignorado = False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._em_titulo = True
        elif tag in ("script", "style"):
            self._em_ignorado = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._em_titulo = False
        elif tag in ("script", "style"):
            self._em_ignorado = False

    def handle_data(self, data):
        if self._em_ignorado:
            return
        texto = data.strip()
        if not texto:
            return
        if self._em_titulo:
            self._partes_titulo.append(texto)
        else:
            self._partes_corpo.append(texto)

    def resultado(self) -> tuple[str, str]:
        return " ".join(self._partes_titulo).strip(), " ".join(self._partes_corpo).strip()


def extrair_texto_de_html(conteudo_html: str) -> tuple[str, str]:
    """(título, texto visível) de um HTML — usado por artigos exportados e por link_intake.py."""
    parser = _ExtratorTextoHTML()
    parser.feed(conteudo_html)
    return parser.resultado()


_TAMANHO_MAX_TRECHO_ARTIGO = 4000


def _extrair_articles_html(pasta_articles: Path) -> list[dict]:
    brutos = []
    for arquivo in sorted(pasta_articles.glob("*.html")):
        conteudo = arquivo.read_text(encoding="utf-8", errors="ignore")
        titulo, corpo = extrair_texto_de_html(conteudo)
        if not corpo and not titulo:
            continue
        trecho = corpo or titulo
        truncado = len(trecho) > _TAMANHO_MAX_TRECHO_ARTIGO
        if truncado:
            trecho = trecho[:_TAMANHO_MAX_TRECHO_ARTIGO] + " [...]"
        brutos.append(
            dict(
                fonte="LinkedIn - Artigo",
                trecho=trecho,
                contexto=f"Artigo publicado no LinkedIn. Título: {titulo or 'não disponível'}. "
                         f"Arquivo: {arquivo.name}. Data não disponível no arquivo exportado."
                         + (" Trecho truncado para caber no contexto." if truncado else ""),
                data="",
            )
        )
    return brutos


EXTRATORES = {
    "shares.csv": _extrair_shares,
    "comments.csv": _extrair_comments,
    "articles.csv": _extrair_articles,
    "positions.csv": _extrair_positions,
    "projects.csv": _extrair_projects,
    "education.csv": _extrair_education,
    "certifications.csv": _extrair_certifications,
    "rich_media.csv": _extrair_rich_media,
    "recommendations_received.csv": _extrair_recommendations,
}


def extrair_evidencias(pasta_entrada: str | Path) -> list[Evidencia]:
    """Lê os arquivos reconhecidos (ver EXTRATORES + pasta Articles/) de uma pasta
    e retorna evidências com ID estável.

    Arquivos ausentes são simplesmente ignorados — nem todo export tem todos os tipos.
    """
    pasta = Path(pasta_entrada)
    if not pasta.is_dir():
        raise FileNotFoundError(f"Pasta de entrada não encontrada: {pasta}")

    brutos: list[dict] = []
    encontrou_algum = False
    for arquivo in pasta.iterdir():
        extrator = EXTRATORES.get(arquivo.name.lower())
        if extrator is None:
            continue
        encontrou_algum = True
        brutos.extend(extrator(arquivo))

    pasta_articles = pasta / "Articles"
    if pasta_articles.is_dir():
        encontrou_algum = True
        brutos.extend(_extrair_articles_html(pasta_articles))

    if not encontrou_algum:
        raise FileNotFoundError(
            f"Nenhum arquivo reconhecido (Shares/Comments/Positions/Projects/Education/"
            f"Certifications/Rich_Media.csv ou pasta Articles/) encontrado em {pasta}"
        )

    return montar_evidencias(brutos)


def montar_evidencias(brutos: list[dict]) -> list[Evidencia]:
    """Ordena por data e atribui ID sequencial estável a uma lista de evidências brutas.

    Evidências sem data (ex.: artigos html, links avulsos) ficam no início da
    ordenação — ainda assim citáveis normalmente.
    """
    brutos_ordenados = sorted(brutos, key=lambda r: r.get("data") or "")
    evidencias = []
    for i, r in enumerate(brutos_ordenados, start=1):
        evidencias.append(
            Evidencia(
                id=f"EV-{i:04d}",
                fonte=r["fonte"],
                trecho=r["trecho"],
                contexto=r["contexto"],
                data=r["data"],
                tema=_classificar_tema(r["trecho"]),
            )
        )
    return evidencias


def acrescentar_evidencias(evidencias_existentes: list[Evidencia], brutos_extra: list[dict]) -> list[Evidencia]:
    """Combina evidências já numeradas com evidências brutas extras (ex.: links avulsos),
    renumerando tudo junto para manter um único ID sequencial e uma ordenação cronológica
    consistente no conjunto final.
    """
    brutos_existentes = [
        dict(fonte=e.fonte, trecho=e.trecho, contexto=e.contexto, data=e.data) for e in evidencias_existentes
    ]
    return montar_evidencias(brutos_existentes + brutos_extra)


def extrair_contexto_nao_citavel(pasta_entrada: str | Path) -> str:
    """Lê Skills.csv, se presente, como contexto agregado — nunca como evidência citável.

    Skills.csv do LinkedIn é só uma lista de nomes de habilidade, sem trecho, data
    ou fonte relacionável a um momento específico — não cabe no schema de evidência
    (id/fonte/trecho/contexto/data/tema) nem faz sentido virar ID citável numa
    hipótese. Por isso vira uma string única de contexto complementar.
    """
    pasta = Path(pasta_entrada)
    caminho = pasta / "Skills.csv"
    if not caminho.is_file():
        return ""

    nomes = []
    for row in _ler_csv(caminho):
        nome = _col(row, "Name") or (next(iter(row.values()), "") or "").strip()
        if nome:
            nomes.append(nome)

    if not nomes:
        return ""

    return "Skills autodeclaradas no perfil do LinkedIn: " + ", ".join(nomes) + "."
