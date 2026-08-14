"""Mapeamento código -> vaga fictícia, usado pelos "links filhos" da experiência
com os 15 profissionais de RH (?codigo=J3 na URL pré-preenche o contexto da vaga).

Textos vindos de vagas ficticias teste1_trama.docx (Projeto TRAMA), 3 vagas
fictícias da mesma empresa fictícia (Confiança Corporativo Ltda.), níveis
crescentes de autonomia — mesmo espírito das 3 vagas da seção 3 do MVP.
"""

_VAGA_JUNIOR = """Vaga A — Analista de RH Júnior (extremo execução)
Empresa fictícia: Confiança Corporativo Ltda. · Nível: Júnior · Experiência: 1–2 anos

Sobre a vaga: Buscamos um(a) Analista de RH Júnior para dar suporte operacional aos subsistemas de recursos humanos, com foco em execução de processos bem definidos e aprendizado das rotinas de RH generalista.

Principais responsabilidades:
- Apoiar processos de recrutamento e seleção de posições operacionais (triagem de currículos, agendamento de entrevistas, aplicação de testes)
- Conduzir onboarding de novos colaboradores e acompanhar documentação de admissão
- Dar suporte ao fechamento da folha de pagamento e controle de ponto
- Atualizar registros e indicadores básicos de RH em planilhas
- Atender dúvidas de primeiro nível de colaboradores sobre benefícios e políticas internas

Requisitos: Ensino superior completo ou cursando em RH, Psicologia, Administração ou áreas correlatas. Pacote Office intermediário. Desejável experiência prévia (estágio ou 1º emprego) em rotinas de departamento pessoal."""

_VAGA_PLENO = """Vaga B — People Partner Pleno (autonomia intermediária)
Empresa fictícia: Confiança Corporativo Ltda. · Nível: Pleno · Experiência: 4–6 anos

Sobre a vaga: Buscamos um(a) People Partner Pleno para atuar como consultor(a) interno(a) das lideranças de uma unidade de negócio, equilibrando execução de subsistemas de RH com autonomia para propor soluções e influenciar decisões de gestão de pessoas.

Principais responsabilidades:
- Atuar como ponto focal de RH para gestores de uma ou mais áreas, apoiando decisões sobre estrutura de equipe, performance e sucessão
- Conduzir processos seletivos de posições de média/alta complexidade de ponta a ponta
- Analisar indicadores de pessoas (turnover, absenteísmo, clima) e propor planos de ação
- Traduzir necessidades do negócio em iniciativas de desenvolvimento e treinamento
- Equilibrar prioridades entre múltiplos líderes com demandas conflitantes

Requisitos: Ensino superior completo em RH, Psicologia, Administração ou áreas correlatas. Experiência consolidada como Business/People Partner ou em posição generalista de RH. Vivência em análise de indicadores e ferramentas de gestão de pessoas."""

_VAGA_SENIOR = """Vaga C — Head de RH (extremo autonomia/gestão)
Empresa fictícia: Confiança Corporativo Ltda. · Nível: Sênior/Liderança · Experiência: 10+ anos

Sobre a vaga: Buscamos um(a) Head de RH para liderar a área e atuar como parceiro(a) estratégico(a) da diretoria, conectando a estratégia de pessoas aos objetivos de negócio em um contexto de ambiguidade e decisões de alto impacto organizacional.

Principais responsabilidades:
- Traduzir a estratégia corporativa em uma agenda de pessoas para a organização, com autonomia para definir prioridades
- Aconselhar a diretoria com base em diagnósticos organizacionais e dados de RH
- Antecipar riscos e oportunidades relacionados a estrutura, talentos e cultura organizacional
- Liderar ciclos de performance, sucessão e desenvolvimento de lideranças
- Construir e gerir o time de RH, definindo sua própria forma de organizar a área

Requisitos: Ensino superior completo, pós-graduação ou MBA em Gestão de Pessoas, Administração ou áreas correlatas. Trajetória sólida em posições de liderança de RH, com histórico de atuação estratégica junto a diretoria/board."""

VAGAS_POR_NIVEL = {
    "J": {"nome": "Júnior", "texto": _VAGA_JUNIOR},
    "M": {"nome": "Pleno/Middle", "texto": _VAGA_PLENO},
    "S": {"nome": "Sênior", "texto": _VAGA_SENIOR},
    # Código de teste interno — não existe linha correspondente na planilha, então
    # nunca é marcado como "usado" (codigo_ja_usado sempre volta False pra ele).
    # Serve pra Pedro testar o fluxo completo (código -> vaga -> planilha -> ntfy)
    # sem consumir nenhum dos 15 links reais dos testadores.
    "T": {"nome": "Teste interno (Pedro)", "texto": _VAGA_JUNIOR},
}

CODIGOS_VALIDOS = [f"{letra}{numero}" for letra in "JMS" for numero in range(1, 6)] + ["T1"]


def vaga_do_codigo(codigo: str) -> dict | None:
    """Retorna {"nome": ..., "texto": ...} para um código válido (ex.: "J3"), ou None."""
    codigo = (codigo or "").strip().upper()
    if codigo not in CODIGOS_VALIDOS:
        return None
    return VAGAS_POR_NIVEL[codigo[0]]
