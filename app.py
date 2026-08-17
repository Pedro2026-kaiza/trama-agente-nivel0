"""Tela inicial (mockup seção 10) + tela do parecer (mockup seção 11) do documento MVP.

Aceita o .zip completo da exportação do LinkedIn. A filtragem por allowlist
(zip_intake.py) garante que só arquivos ligados à trajetória profissional são
sequer lidos; todo o resto do zip nunca é aberto. A pasta temporária usada na
extração é sempre apagada ao final (intake.py), com sucesso ou erro.

Os campos "Outra fonte" e o seletor Candidato/Recrutador seguem o mockup, mas
ainda não alteram o comportamento do pipeline — isso seria conectores/modos
adicionais, fora do escopo do Nível 0 (Direcionamento_Nivel_0_Claude_Code.docx,
seção 2).
"""
import io
import json
import threading
import time

import streamlit as st

from codigo_tracking import codigo_ja_usado, marcar_codigo_usado
from extractor import acrescentar_evidencias
from intake import processar_zip_linkedin
from link_intake import buscar_evidencia_de_link, buscar_texto_vaga
from notificacoes import notificar_conclusao
from pipeline import montar_parecer
from vagas_config import vaga_do_codigo


def _rodar_com_progresso(mensagem: str, fn, *args, **kwargs):
    """Roda fn em background e mostra um contador de tempo decorrido.

    Sem isso, uma chamada que leva minutos (comum em exports reais grandes)
    parece travada atrás de um st.spinner mudo. Streamlit roda o script no
    servidor: recarregar a página no meio reinicia o processo do zero, então
    o aviso deixa isso explícito.
    """
    resultado: dict = {}
    erro: dict = {}

    def alvo():
        try:
            resultado["valor"] = fn(*args, **kwargs)
        except Exception as e:  # relançado na thread principal abaixo
            erro["valor"] = e

    thread = threading.Thread(target=alvo, daemon=True)
    thread.start()

    placeholder = st.empty()
    inicio = time.time()
    while thread.is_alive():
        decorrido = int(time.time() - inicio)
        placeholder.info(
            f"⏳ {mensagem} ({decorrido}s decorridos)\n\n"
            "Exports com bastante atividade podem levar alguns minutos — isso é "
            "esperado, não é travamento. **Não recarregue a página**: isso reinicia "
            "o processo do zero em vez de retomá-lo."
        )
        time.sleep(1)
    placeholder.empty()

    if "valor" in erro:
        raise erro["valor"]
    return resultado["valor"]

st.set_page_config(page_title="Agente Investigativo", page_icon="🔍", layout="centered")

st.title("AGENTE INVESTIGATIVO")
st.markdown(
    "**Não estamos tentando descobrir quem o profissional é.**\n\n"
    "**Estamos investigando o que sua trajetória parece contar.**"
)
st.write(
    "O agente analisa evidências públicas e fontes autorizadas, conecta experiências "
    "ao longo do tempo e levanta hipóteses para que o recrutador possa investigá-las em entrevista."
)

st.divider()

# Gate de acesso: esta é uma ferramenta fechada por convite nesta fase de testes.
# Sem código válido e ainda não usado, ninguém passa daqui — evita que o link, se
# vazar, gere chamadas reais (e cobradas) à API por qualquer pessoa sem convite.
codigo_url = st.query_params.get("codigo", "")
vaga_pre_carregada = vaga_do_codigo(codigo_url) if codigo_url else None

if not vaga_pre_carregada:
    if codigo_url:
        st.error(
            f"Código \"{codigo_url}\" não reconhecido. Verifique o link que você recebeu, "
            "ou entre em contato com quem te convidou."
        )
    else:
        st.error("Este é um teste fechado, por convite. Acesse pelo link com o código que você recebeu.")
    st.stop()

if codigo_ja_usado(codigo_url):
    st.error(
        "Este link já foi utilizado. Se você acredita que isso é um engano, entre em "
        "contato com quem te enviou o convite."
    )
    st.stop()

st.info(f"Vaga carregada automaticamente para o código **{codigo_url.upper()}** (nível {vaga_pre_carregada['nome']}).")

modo = st.radio("Modo", ["Candidato", "Recrutador"], horizontal=True)
st.caption("O modo ainda não muda o comportamento do pipeline nesta fase (Nível 0).")

contexto_vaga = st.text_area(
    "Contexto da vaga (opcional)",
    value=vaga_pre_carregada["texto"] if vaga_pre_carregada else "",
    placeholder=(
        "Você pode preencher este campo de dois jeitos:\n"
        "1. Cole aqui o texto completo da descrição da vaga; ou\n"
        "2. Cole apenas o link da vaga — nesta fase de testes, só aceitamos links do "
        "LinkedIn (linkedin.com/jobs/...)."
    ),
    height=120,
)

st.markdown("**Exportação de dados do LinkedIn** \\*")
arquivo_zip = st.file_uploader(
    "Envie o .zip completo da exportação de dados do LinkedIn (Configurações e Privacidade → "
    "Privacidade de dados → Obter uma cópia dos seus dados)",
    type="zip",
    accept_multiple_files=False,
    label_visibility="collapsed",
)
st.caption(
    "Aceitamos o .zip completo do LinkedIn — nosso sistema lê automaticamente apenas os "
    "arquivos relacionados à sua trajetória profissional e descarta o resto sem processar ou armazenar."
)

col1, col2 = st.columns(2)
with col1:
    outra_fonte_1 = st.text_input("Outra fonte", placeholder="https://...", key="outra_fonte_1")
with col2:
    outra_fonte_2 = st.text_input("Outra fonte", placeholder="https://...", key="outra_fonte_2")
st.caption(
    "Use aqui um link que qualquer pessoa consiga abrir e ler na hora, sem precisar de login "
    "— como um portfólio pessoal, um site de projetos ou uma página \"sobre mim\". "
    "Infelizmente, links do Google Drive e OneDrive não funcionam aqui: eles costumam pedir "
    "login ou abrir numa tela que nosso sistema não consegue ler."
)

autorizado = st.button(
    "Autorizar análise e iniciar investigação",
    type="primary",
    disabled=arquivo_zip is None,
)

if autorizado:
    with st.spinner("Extraindo evidências..."):
        try:
            evidencias, contexto_nao_citavel = processar_zip_linkedin(io.BytesIO(arquivo_zip.getvalue()))
        except Exception as e:
            st.error(f"Falha na extração: {e}")
            st.stop()

        brutos_links = []
        for link in (outra_fonte_1, outra_fonte_2):
            if not link.strip():
                continue
            bruto, aviso = buscar_evidencia_de_link(link)
            if bruto:
                brutos_links.append(bruto)
            if aviso:
                st.warning(aviso)
        if brutos_links:
            evidencias = acrescentar_evidencias(evidencias, brutos_links)

        contexto_vaga_resolvido, aviso_vaga = buscar_texto_vaga(contexto_vaga)
        if aviso_vaga:
            st.warning(aviso_vaga)

    try:
        resultado = _rodar_com_progresso(
            "Gerando parecer...",
            montar_parecer,
            evidencias,
            contexto_nao_citavel=contexto_nao_citavel,
            contexto_vaga=contexto_vaga_resolvido,
        )
    except Exception as e:
        st.error(f"Falha ao gerar o parecer: {e}")
        st.stop()

    if vaga_pre_carregada:
        marcar_codigo_usado(codigo_url)
        notificar_conclusao(codigo_url, vaga_pre_carregada["nome"])

    st.divider()
    st.header(f"PARECER INVESTIGATIVO — {modo.upper()}")

    evidencias_por_id = {e["id"]: e for e in resultado.get("evidencias_extraidas") or []}
    hipoteses = resultado.get("hipoteses") or []
    n_alta = sum(1 for h in hipoteses if h.get("confianca") == "Alta")
    n_media = sum(1 for h in hipoteses if h.get("confianca") == "Média")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Evidências analisadas", resultado["_meta"]["total_evidencias"])
    c2.metric("Hipóteses validadas", len(hipoteses))
    c3.metric("Confiança alta", n_alta)
    c4.metric("Confiança média", n_media)

    with st.expander("CONTEXTO DA ANÁLISE", expanded=True):
        st.write(resultado.get("contexto_analise") or "—")

    if contexto_vaga_resolvido.strip():
        with st.expander("LEITURA EM RELAÇÃO AO CONTEXTO DA VAGA", expanded=True):
            st.caption(
                "Conexões e prioridades a partir do que foi descrito na vaga — não é um veredito "
                "de adequação, aprovação ou pontuação."
            )
            st.write(resultado.get("leitura_vs_contexto_da_vaga") or "—")

    ids_relevantes = sorted({eid for h in hipoteses for eid in h["evidencias_citadas"]})
    with st.expander(f"EVIDÊNCIAS MAIS RELEVANTES ({len(ids_relevantes)} citadas em hipóteses)", expanded=True):
        if ids_relevantes:
            st.caption(
                "As colunas de texto aparecem cortadas por causa do tamanho da célula, não porque "
                "o conteúdo foi cortado — clique duas vezes numa célula pra ler o texto inteiro."
            )
            st.dataframe(
                [
                    {
                        "ID": eid,
                        "Fonte": evidencias_por_id[eid]["fonte"],
                        "Data": evidencias_por_id[eid]["data"],
                        "Trecho": evidencias_por_id[eid]["trecho"],
                        "Contexto": evidencias_por_id[eid]["contexto"],
                    }
                    for eid in ids_relevantes
                ],
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.write("Nenhuma evidência foi citada em hipótese válida.")

    with st.expander("PADRÕES EMERGENTES", expanded=True):
        for p in resultado.get("padroes_emergentes") or []:
            st.markdown(f"- {p}")

    with st.expander("NARRATIVA PROFISSIONAL", expanded=True):
        st.write(resultado.get("narrativa_profissional") or "—")

    with st.expander("FORÇAS EVIDENCIADAS", expanded=True):
        for f in resultado.get("forcas_evidenciadas") or []:
            st.markdown(f"- {f}")

    with st.expander("TENSÕES E LACUNAS", expanded=True):
        for t in resultado.get("tensoes_e_lacunas") or []:
            st.markdown(f"- {t}")

    with st.expander("HIPÓTESES A VALIDAR", expanded=True):
        for h in hipoteses:
            fontes_distintas = {evidencias_por_id[eid]["fonte"] for eid in h["evidencias_citadas"]}
            with st.expander(f"{h['id_hipotese']} · confiança: {h.get('confianca')} — {h['descricao'][:80]}..."):
                st.write(h["descricao"])

                m1, m2, m3 = st.columns(3)
                m1.metric("Confiança", h.get("confianca"))
                m2.metric("Evidências citadas", len(h["evidencias_citadas"]))
                m3.metric("Fontes distintas", len(fontes_distintas))
                if h.get("contradicao_entre_evidencias_citadas"):
                    st.caption("⚠️ O modelo sinalizou contradição entre as evidências citadas nesta hipótese.")

                st.markdown(f"**Evidências citadas:** {', '.join(h['evidencias_citadas'])}")
                st.markdown(f"**Contexto:** {h.get('contexto', '—')}")
                st.markdown(f"**O que permanece desconhecido:** {h.get('o_que_permanece_desconhecido', '—')}")
                st.markdown("**Perguntas de validação:**")
                for q in h.get("perguntas_validacao") or []:
                    st.markdown(f"- {q}")

        rejeitadas = resultado.get("hipoteses_rejeitadas_por_citacao_invalida") or []
        if rejeitadas:
            st.warning(f"{len(rejeitadas)} hipótese(s) descartada(s) por citar evidência inexistente.")
            with st.expander("Hipóteses rejeitadas (checagem de citação)"):
                st.json(rejeitadas)

    with st.expander("PERGUNTAS DE ENTREVISTA", expanded=True):
        for q in resultado.get("perguntas_entrevista") or []:
            st.markdown(f"- {q}")

    with st.expander("LIMITAÇÕES DA ANÁLISE"):
        st.write(resultado.get("limitacoes_da_analise") or "—")

    st.divider()
    st.download_button(
        "Baixar parecer completo (JSON)",
        data=json.dumps(resultado, ensure_ascii=False, indent=2),
        file_name="parecer.json",
        mime="application/json",
    )
