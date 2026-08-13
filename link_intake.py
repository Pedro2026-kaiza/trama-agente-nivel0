"""Extração de evidência a partir de um link genérico fornecido manualmente pelo
usuário (campos "Outra fonte" da Tela 1) — não faz parte do export do LinkedIn,
e é buscado ao vivo (única parte do pipeline que faz uma requisição de rede
para um endereço fornecido pelo próprio usuário, não sugerido por conteúdo
de terceiros).

Funciona bem para páginas públicas simples (landing pages, portfólios pessoais,
páginas de projeto). NÃO é confiável para links do Google Drive/Docs/Sheets:
esses geralmente respondem com uma página de visualização renderizada via
JavaScript, não o conteúdo real do documento — nesse caso a extração tende a
vir vazia e a função retorna um aviso em vez de forçar uma evidência ruim.
"""
from __future__ import annotations

import ipaddress
import socket
import urllib.request
from urllib.parse import urlparse

from extractor import extrair_texto_de_html

TAMANHO_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
TIMEOUT_SEGUNDOS = 10
TAMANHO_MAX_TRECHO = 4000
USER_AGENT = "Mozilla/5.0 (compatible; AgenteInvestigativoNivel0/1.0)"


def _host_e_seguro(hostname: str) -> bool:
    """Bloqueia endereços locais/internos (proteção básica contra SSRF)."""
    try:
        ip = ipaddress.ip_address(socket.gethostbyname(hostname))
    except (socket.gaierror, ValueError, OSError):
        return False
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast)


def _buscar_html(url: str) -> tuple[str | None, str | None]:
    """Busca uma URL e retorna (conteudo_html, erro). Guarda de SSRF + tamanho embutida."""
    partes = urlparse(url)
    if partes.scheme not in ("http", "https") or not partes.hostname:
        return None, "precisa começar com http:// ou https://"

    if not _host_e_seguro(partes.hostname):
        return None, "endereço não permitido"

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEGUNDOS) as resp:
            content_type = (resp.headers.get("Content-Type") or "").lower()
            if "html" not in content_type:
                return None, "conteúdo não é uma página web legível (HTML)"
            bruto_bytes = resp.read(TAMANHO_MAX_BYTES)
            encoding = resp.headers.get_content_charset() or "utf-8"
            return bruto_bytes.decode(encoding, errors="ignore"), None
    except Exception as e:
        return None, str(e)


def buscar_evidencia_de_link(url: str) -> tuple[dict | None, str | None]:
    """Busca um link e tenta extrair evidência dele.

    Retorna (bruto, aviso): bruto é um dict pronto para extractor.acrescentar_evidencias
    (ou None se nada útil foi extraído); aviso é uma mensagem para mostrar ao usuário
    quando bruto é None ou quando algo relevante aconteceu.
    """
    url = url.strip()
    conteudo, erro = _buscar_html(url)
    if erro:
        return None, f"Link ignorado ({erro} — comum em links do Google Drive/OneDrive): {url}"

    titulo, corpo = extrair_texto_de_html(conteudo)
    trecho = corpo or titulo
    if not trecho:
        return None, f"Link acessado, mas sem texto legível extraído (comum em links do Google Drive/OneDrive): {url}"

    truncado = len(trecho) > TAMANHO_MAX_TRECHO
    if truncado:
        trecho = trecho[:TAMANHO_MAX_TRECHO] + " [...]"

    bruto = dict(
        fonte="Fonte adicional (link)",
        trecho=trecho,
        contexto=(
            f"Conteúdo obtido de link fornecido manualmente pelo usuário (fora do export do "
            f"LinkedIn). Título: {titulo or 'não disponível'}. URL: {url}."
            + (" Trecho truncado para caber no contexto." if truncado else "")
        ),
        data="",
    )
    return bruto, None


def buscar_texto_vaga(texto_ou_link: str) -> tuple[str, str | None]:
    """Resolve o campo "Contexto da vaga" da Tela 1.

    Se vier um link, nesta fase de testes só aceitamos link do LinkedIn (linkedin.com)
    e tentamos extrair o texto da página. Se vier texto comum, é a descrição colada
    diretamente — usada como está. Retorna (texto_resolvido, aviso).
    """
    texto = texto_ou_link.strip()
    if not texto:
        return "", None

    partes = urlparse(texto)
    parece_link = partes.scheme in ("http", "https") and bool(partes.hostname)
    if not parece_link:
        return texto, None

    if "linkedin.com" not in partes.hostname.lower():
        return "", (
            "Nesta fase de testes só aceitamos link de vaga do LinkedIn — cole o texto "
            f"completo da vaga, ou um link linkedin.com/jobs/...: {texto}"
        )

    conteudo, erro = _buscar_html(texto)
    if erro:
        return "", f"Não foi possível ler o link da vaga ({erro}). Cole o texto da vaga diretamente: {texto}"

    titulo, corpo = extrair_texto_de_html(conteudo)
    resolvido = corpo or titulo
    if not resolvido:
        return "", f"Não foi possível extrair texto do link da vaga. Cole o texto da vaga diretamente: {texto}"

    truncado = len(resolvido) > TAMANHO_MAX_TRECHO
    if truncado:
        resolvido = resolvido[:TAMANHO_MAX_TRECHO] + " [...]"
    return resolvido, None
