"""Extração de evidência a partir de um PDF do perfil do LinkedIn enviado
diretamente — alternativa ao .zip completo, pra quando o candidato prefere usar
o "Salvar como PDF" do próprio perfil (mais simples) em vez do export de dados
completo. É uma fonte auto-autorizada (o próprio candidato gera e envia), só que
mais rasa: um PDF de perfil só traz o resumo/cargos/formação como aparecem na
tela, não o histórico de posts/comentários/artigos que o .zip traz.
"""
from __future__ import annotations

import io

import pypdf

TAMANHO_MAX_TRECHO = 6000  # perfis podem ser mais longos que um post; margem maior
TAMANHO_MINIMO_TEXTO = 40


def extrair_evidencia_de_pdf(conteudo_bytes: bytes, nome_arquivo: str = "perfil.pdf") -> tuple[dict | None, str | None]:
    """Extrai texto de um PDF de perfil do LinkedIn e retorna (bruto, aviso).

    bruto é um dict pronto para extractor.montar_evidencias/acrescentar_evidencias
    (ou None se nada útil foi extraído); aviso é uma mensagem pra mostrar ao usuário
    quando bruto é None (ex.: PDF escaneado sem OCR, corrompido, protegido por senha).
    """
    try:
        leitor = pypdf.PdfReader(io.BytesIO(conteudo_bytes))
        if leitor.is_encrypted:
            return None, f"O PDF \"{nome_arquivo}\" está protegido por senha — não conseguimos ler o conteúdo."
        paginas = [pagina.extract_text() or "" for pagina in leitor.pages]
    except Exception as e:
        return None, f"Não foi possível ler o PDF \"{nome_arquivo}\" ({e})."

    texto = "\n".join(paginas).strip()
    if len(texto) < TAMANHO_MINIMO_TEXTO:
        return None, (
            f"O PDF \"{nome_arquivo}\" foi lido, mas sem texto legível suficiente "
            "(comum em PDFs escaneados como imagem, sem OCR)."
        )

    truncado = len(texto) > TAMANHO_MAX_TRECHO
    if truncado:
        texto = texto[:TAMANHO_MAX_TRECHO] + " [...]"

    bruto = dict(
        fonte="LinkedIn - Perfil (PDF)",
        trecho=texto,
        contexto=(
            f"Conteúdo extraído do PDF do perfil do LinkedIn enviado diretamente (arquivo: "
            f"{nome_arquivo}) — não é o export de dados completo, então não traz histórico de "
            "posts, comentários ou artigos, só o que aparece na tela do perfil no momento do envio."
            + (" Trecho truncado para caber no contexto." if truncado else "")
        ),
        data="",
    )
    return bruto, None
