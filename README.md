# Agente Investigativo de Trajetórias Profissionais — Nível 0

Implementação conforme `Direcionamento_Nivel_0_Claude_Code.docx`, mais uma tela em
Streamlit (mockups das seções 10 e 11 do documento MVP) construída depois, por pedido
explícito do usuário — o próprio Direcionamento marca UI como fora do núcleo original,
mas o texto também prevê esse tipo de decisão futura ("me avise... mas não implemente
sem eu confirmar"), então cada desvio do escopo original está documentado aqui e nos
commits/mensagens da sessão. Continua sem banco de dados, sem autenticação de usuário,
sem embeddings/busca semântica.

## Arquivos

- `zip_intake.py` — extração segura do `.zip` completo da exportação do LinkedIn:
  allowlist rígida (só os arquivos ligados à trajetória profissional saem do zip;
  o resto nunca é lido, nem sequer aberto), guarda contra zip-slip e contra arquivo
  anormalmente grande.
- `intake.py` — orquestra `zip_intake.py` + `extractor.py` numa pasta temporária que é
  sempre apagada ao final (`tempfile.TemporaryDirectory`), com sucesso ou erro.
- `extractor.py` — lê os arquivos permitidos (Shares/Comments/Positions/Projects/
  Education/Certifications/Rich_Media/Recommendations_Received.csv, mais `Articles/*.html`)
  de uma pasta e produz evidências `{id, fonte, trecho, contexto, data, tema}`. 100%
  determinístico, nenhuma chamada a modelo. `tema` usa um classificador simples por
  palavra-chave (ver `TEMA_KEYWORDS`) — ponto de partida, não taxonomia definitiva; o
  agente de raciocínio (etapa 2) é quem de fato encontra os padrões finos.
  `Skills.csv` é tratado à parte (`extrair_contexto_nao_citavel`): vira uma string de
  contexto agregado, nunca uma evidência com ID citável — não faz sentido no schema
  (sem trecho/data/fonte relacionável a um momento).
- `master_prompt.py` — texto exato do prompt mestre (seção 4 do Direcionamento) e a
  montagem da mensagem enviada com todas as evidências + schema de saída em JSON.
- `confidence.py` — regra de confiança da seção 5, calculada em código:
  - 3+ evidências, de 2+ fontes distintas, sem contradição → **Alta**
  - 1–2 evidências, ou evidências de uma única fonte → **Média**
  - Sem evidência válida nenhuma → não vira hipótese (fica em `tensoes_e_lacunas`)
- `validation.py` — checagem de citação da seção 6: qualquer hipótese que cite um ID
  de evidência inexistente na lista extraída é **descartada inteira** antes de chegar
  ao resultado final (fica registrada em `hipoteses_rejeitadas_por_citacao_invalida`
  para depuração, mas não é apresentada como parecer válido).
- `link_intake.py` — busca ao vivo de 1 link genérico (campos "Outra fonte" da Tela 1):
  só HTTP/HTTPS, guarda básica contra SSRF (recusa localhost/IP privado/link-local),
  limite de tamanho, extrai texto visível de HTML. Não é confiável para Google
  Drive/Docs/Sheets (respondem com página de visualização em JS, não o conteúdo real) —
  nesse caso retorna aviso em vez de forçar uma evidência vazia/ruim.
- `pipeline.py` — liga tudo e faz a chamada à API da Anthropic.
- `main.py` — CLI (pasta local, fluxo original do Nível 0).
- `app.py` — Streamlit: tela de upload do `.zip` (mockup seção 10) → tela do parecer
  organizada em `st.expander`/`st.metric` por seção (mockup seção 11).

### Decisão de design: contexto da vaga e links extras (pedido explícito do usuário)

Depois de um teste real na Tela 1, o usuário notou duas lacunas: (1) o campo "Contexto
da vaga" já existia na UI mas nunca era passado ao modelo — bug de UI incompleta, não
scope creep, já estava previsto desde a seção 4 do MVP ("Descrição da vaga: Recomendado");
(2) os campos "Outra fonte" estavam inertes. Ambos corrigidos:

- `contexto_vaga` agora chega ao modelo e gera uma seção nova, `leitura_vs_contexto_da_vaga`
  — mas com instrução explícita para NUNCA virar avaliação de adequação/aprovação/pontuação,
  só apontar quais evidências/hipóteses/perguntas já formuladas se conectam ao que foi
  descrito na vaga. Isso preserva o princípio central do projeto (o agente não decide
  quem é bom ou ruim) mesmo com o novo campo.
- Os 2 campos "Outra fonte" agora buscam o link ao vivo (`link_intake.py`) e viram
  evidência com `fonte = "Fonte adicional (link)"`, mescladas às evidências do LinkedIn
  via `extractor.acrescentar_evidencias` (renumera tudo junto, mantendo um único ID
  sequencial). Isso é tecnicamente território de "conector" (Nível 1, Doc 2 seção 6.2,
  normalmente gated por sinal de experimento) — decisão consciente do usuário de
  adiantar, não uma escolha unilateral da engenharia.

### Decisão de design: Recommendations_Received.csv (recomendações de terceiros)

O Direcionamento e o MVP originalmente marcam "depoimentos de terceiros" como fora do
núcleo até a questão de consentimento ser resolvida. Confirmado explicitamente pelo
usuário durante a sessão: incluir esse arquivo agora, com a leitura de que é um recurso
nativo e opt-in do LinkedIn (quem recomenda escolhe publicar). Essas evidências saem
com `fonte = "LinkedIn - Recomendação recebida (terceiro)"` e o `contexto` sempre
começa com "ESCRITA POR TERCEIRO" — nunca escondemos a origem. Recomendações com
`Status` contendo "revoke" são descartadas na extração.

### Decisão de design: como "sem contradição" é avaliado

O Direcionamento é explícito que a confiança nunca é auto-reportada pelo modelo — e
isso é respeitado à risca aqui: o **grau** de confiança (Alta/Média) é sempre calculado
em `confidence.py`, nunca pedido ao modelo. Mas a regra de "Alta" depende de as
evidências citadas não se contradizerem entre si, e isso é uma leitura semântica do
texto que o código não consegue fazer sozinho. Por isso o modelo retorna, por hipótese,
apenas um sinal factual binário (`contradicao_entre_evidencias_citadas: true/false`) —
não uma nota de confiança — e o código aplica a regra determinística em cima disso,
junto com a contagem de evidências e fontes distintas (essa contagem é recalculada em
código a partir da lista real de evidências, então nem esse componente pode ser
inflado pelo modelo).

## Uso

```bash
pip install -r requirements.txt

# CLI — pasta local com CSVs já extraídos (fluxo original do Nível 0)
python main.py --input "../" --dry-run          # só extração, sem custo de API
python main.py --input "../" --output parecer.json   # precisa de ANTHROPIC_API_KEY (.env)

# Interface Streamlit — aceita o .zip completo da exportação do LinkedIn
streamlit run app.py
```

`--input` do CLI deve apontar para uma pasta com os arquivos já soltos (não o `.zip`).
O dado fictício de teste está na raiz de `Projeto TRAMA/` (ver `LEIA-ME.md` ali) — por
isso os exemplos acima usam `--input "../"`.

O `app.py` (Streamlit) já aceita o `.zip` bruto, exatamente como sai do LinkedIn
("Baixar seus dados" → arquivo maior): filtra pela allowlist de `zip_intake.py`,
extrai numa pasta temporária e apaga tudo ao final — nada do zip ou dos arquivos
extraídos sobra em disco.

## O que conferir depois de rodar

1. Toda evidência em `evidencias_extraidas` tem os 6 campos preenchidos.
2. Toda hipótese em `hipoteses` cita pelo menos um ID que existe de fato em
   `evidencias_extraidas` (garantido em código — não deveria haver exceção).
3. `hipoteses_rejeitadas_por_citacao_invalida` deveria vir vazio na maioria dos casos;
   se não vier, é sinal de alucinação de citação pelo modelo, que o filtro pegou.
4. O campo `confianca` de cada hipótese bate com a regra da seção 5 dado o número de
   evidências citadas e fontes distintas.

## Fora de escopo nesta fase (não implementado de propósito)

Embeddings/busca semântica/vector DB, grafo ou modelagem temporal separada,
persistência multiusuário, autenticação, conectores automatizados para outras
plataformas, scraping, e qualquer score único/ranking/matching. UI foi liberada por
pedido explícito do usuário (ver topo deste README) — o resto da lista do Direcionamento
(seção 2) continua valendo até sinal do experimento justificar.

Dentro do `.zip` do LinkedIn, ficam **fora da allowlist** (nunca extraídos, nunca
lidos): `messages.csv`, `PhoneNumbers.csv`, `Email Addresses.csv`,
`Whatsapp Phone Numbers.csv`, `Ad_Targeting.csv`, `Receipts_v2.csv`,
`Registration.csv`, arquivos de Job Applications, `Connections.csv`,
`Invitations.csv`, e qualquer arquivo fora da lista em `zip_intake.CSV_PERMITIDOS`.
