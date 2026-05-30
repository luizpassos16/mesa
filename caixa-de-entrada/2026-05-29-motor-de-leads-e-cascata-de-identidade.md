# Motor de leads + cascata de identidade (matéria-prima)

> Capturado em 2026-05-29 a partir de conversa de voz do Luiz. É material **cru**
> (caixa-de-entrada). Algumas decisões já foram tomadas e executadas — ver no fim.

## A grande sacada
Comunidade, Board, Cursos, Eventos e Produtos de Educação **não são o produto**. São
**pontos de contato** com o empresário, e cada um extrai um tipo de informação:
- Formulário de evento de educação → um conjunto de dados
- Lista de interesse / comunidade → faturamento, dores
- Board → outro conjunto, mais profundo

O **produto de verdade é o banco de dados de pessoas** que se forma no cruzamento desses
pontos. Um **motor de leads proprietário**. A sacada é **não distribuir esses leads**
(não dar pra patrocinador, não dar pra outras frentes) e sim acumular pra mim.

## Para onde isso vai
- Curto prazo: organizar os dados espalhados em um sistema único.
- Médio: uma **consultoria** onde um consultor "comum" abre a ficha e já tem todo o
  histórico da pessoa pra dar respostas melhores (com IA por trás).
- Longo: o acúmulo de leads ao longo dos anos vira um ativo / um negócio.
- Hoje: "temos um negócio, ainda não uma empresa." O foco é construir o **topo de funil**
  e o banco de dados por baixo dele.

## Fontes hoje (espalhadas)
Notion · Tally (formulários) · transcrições (Granola, Zoom) · Google Drive · e-mail ·
agenda · pontos de contato avulsos com empresários.

## Decisões tomadas nesta sessão
1. **Arquitetura:** estender o Supabase **MESA** atual (não criar base separada).
2. **Entidade central:** NÃO existe registro mestre. Existe uma **cascata de chaves de
   identidade** em ordem de força (email → telefone → instagram → nome). Tenta uma; se
   não tiver, vai pra próxima. Reconcilia a mesma pessoa entre formulários com campos
   diferentes (tem form que só vem nome; outro vem email).
3. **Começar:** testar **uma fonte ponta a ponta** antes de generalizar.

## O que foi construído e testado (✔ executado no Supabase MESA)
Camada de pessoas/CRM nova, com RLS ligado (fechada pra API pública):
- `people` — a pessoa unificada (ficha).
- `person_identities` — as chaves da cascata (email/phone/instagram/name), únicas.
- `source_submissions` — o ponto de contato cru, com proveniência e idempotência.
- Função `resolve_person(...)` — o motor de cascata, tolerante a lixo ("N", "a", "0",
  instagram sem letra). Match só por nome marca `needs_review`.
- `ingest_tally_newmembers(...)` — ingestor idempotente do form Tally.

**Fonte testada:** Tally "FORMULARIO PARA NOVOS MEMBROS" (`wbvQx1`), 155 respostas.

**Resultado:** 155 submissões → **150 pessoas** (113 com email, 37 só telefone),
**5 fusões automáticas**:
- ✅ Thiago Teixeira (2× por email), Antonio Moreno (2× por email/telefone,
  inclusive nomes diferentes "Antonio Moreno" e "Antonio de Souza Moreno"),
  Luiz Passos (2× por telefone).
- ⚠️ "teste/Teste" fundiu só por nome → **marcado pra revisão** (lixo de teste).
- ❌ Rita Leão + Marcelo Leão fundiram por **telefone compartilhado** (casal/sócios) →
  **falso positivo**. Limitação conhecida da cascata.

## Aprendizados / próximos passos (não decididos ainda)
- **Telefone compartilhado** precisa de regra extra (ex.: se nomes muito diferentes, não
  fundir sozinho — marcar revisão). Casal/sócios usam o mesmo número.
- **Qualidade do dado:** muito lixo nos campos abertos e em datas de nascimento (formatos
  variados, idade "33" em vez de data). Os campos qualitativos longos (motivação, maior
  dificuldade, apresentação) NÃO foram ingeridos neste teste — são o "ouro pra IA" e
  devem entrar por um job dedicado (Edge Function chamando a API do Tally direto, sem
  passar pelo assistente).
- **Enriquecimento entre fontes:** o mesmo motor serve pras outras 42 fontes do Tally e
  pras demais (Notion, Granola, Zoom, Drive, Gmail, Agenda).
- **RLS legado:** as 57 tabelas antigas do app MESA estão com RLS desligado (buraco de
  segurança) — tarefa separada.
- **Mapear "maior dificuldade"** → `pain_areas`/`diagnoses`; respostas abertas →
  `member_insights`; embeddings (`member_embeddings`, pgvector já instalado) pra busca
  semântica na ficha.

## Fase 2 — 2ª fonte Tally + enriquecimento cross-fonte (✔ executado)
**Fonte:** Tally "A MESA | CONEXÃO ENTRE OS MEMBROS" (`mDyqRZ`), 72 respostas.
Escolhida por ter **CPF** (chave forte de verdade) + dados de negócio (faturamento,
segmento) + campos qualitativos ricos (trajetória, desafio, o que busca).

**O que mudou no motor:**
- **CPF entrou na cascata** como 2ª chave mais forte: email → **cpf** → telefone →
  instagram → nome. `norm_cpf()` exige 11 dígitos e rejeita sequência repetida.
- Nova tabela **`person_insights`** (RLS ligado) — guarda o qualitativo por pessoa:
  `about`, `challenge`, `trajectory`, `goal`, `lifestyle`. É o "ouro pra IA".
- Novo campo `people.monthly_revenue_range`.
- `resolve_person()` agora **enriquece** ficha existente (só preenche campo vazio).

**Resultado:** 155 + 72 = **227 submissões → 202 pessoas**. 32 CPFs, 320 insights,
67 com faixa de faturamento. **15 pessoas apareceram nas DUAS fontes** e foram
reconciliadas (não duplicadas) — ex.: Pedro Grenfell ganhou CPF + 2º email + nome
completo, ficando com 7 chaves. **Prova do enriquecimento cross-fonte.**

**Aprendizado-chave (do Luiz):** "não preciso só de chaves, preciso de DADO por pessoa."
As chaves são o esqueleto (não duplicar); o valor está nos atributos + qualitativo.
A ficha agora tem identificação + dados de negócio + 5 insights + pontos de contato.

**3 bugs de qualidade pegos e corrigidos:**
1. Texto qualitativo estava sendo normalizado (minúscula/sem acento) — agora guarda
   **original** (`norm_text` só nas chaves, nunca no texto livre/display).
2. Empresa/cargo/nome perdiam maiúsculas — corrigido (case preservado).
3. Faturamento vinha como array cru `["R$..."]` — agora limpo.
   Limpeza feita direto do `raw_payload` já gravado (sem rebuscar no Tally).

## Aprendizados / próximos passos (pós fase 2)
- **Telefone compartilhado** ainda funde casal/sócios silenciosamente — CPF resolve a
  maioria dos casos novos, mas falta a regra "nomes muito diferentes → revisar".
- **Qualitativo do form 1** (`wbvQx1`) ✔ extraído em sessão posterior.
- **Escala:** padrão de ingestor idempotente serviu pras outras 41 fontes — ver Fase 3.
- **RLS legado:** 57 tabelas antigas seguem abertas (ERROs no advisor) — tarefa separada.
- **member_embeddings** (pgvector instalado): próximo passo natural com qualitativo populado.

## Fase 3 — Ingestão de todas as fontes Tally (✔ executado 2026-05-30)
43 formulários inspecionados. 41 ingeridos. 2 bloqueados por bug `label: null` no MCP Tally:
- ❌ `3xq8e9` "Café com Zema" (69 sub) — bloqueado.
- ❌ `wgE0G1` "Confirmação BOPE" (23 sub) — bloqueado.

**O que foi construído:**
- Re-ingestão do form 1 com campos qualitativos (submissões antigas não tinham; re-fetch
  do Tally atualiza o `raw_payload` via ON CONFLICT DO UPDATE).
- `ingest_tally_confirmacao(...)` — genérico parameterizado para confirmações de evento.
- 21 ingestores específicos (ver tabela completa no apêndice técnico).

**Tipos de qualitativo capturado:**
- motivation: form1 (wbvQx1), interesse (mVglxl), resgate (3NKlrN)
- pain: form1, interest, board2602, ia_imersao, jantar_one, mesa_ia, onboarding,
  advisory, board_form (VL8N8N), mentoria (mRp12j)
- wish: form1, indicacoes, jantar_outside, ia_imersao, jantar_one, mesa_ia,
  advisory, mesa_aberta_vaga (5Be9AM), mentoria, imersao_ia (jaGkva)
- about: conexao, indicacoes, onboarding, bedeal, satisfacao_geral,
  satisfacao_mesa_ia_evento (rjkBV5), satisfacao_ia_int (2EL44j), mentoria
- challenge: 2026, board2602, onboarding, board_form, mentoria
- trajectory: conexao, board_meeting, board2602, board_form, mentoria
- goal: conexao, 2026, onboarding, mentoria
- intro_phrase: form1, indicacoes, satisfacao_geral
- lifestyle: conexao
- about: satisfacao_mesa_ia_evento, satisfacao_ia_int

**Resultado: 427 pessoas · 773 submissões · 1.643 insights**
+31 pessoas novas das 68 submissões desta fase (maioria reconciliou com existentes via cascata).

## Fase 4 — Auditoria de unicidade + limpeza de fusões (✔ executado 2026-05-30)
Pergunta do Luiz: "as 427 são únicas ou estamos repetindo?". Auditoria achou os DOIS defeitos:

**🔴 Fusões ERRADAS (pessoas diferentes na mesma ficha) — 5 fichas, corrigidas:**
- **"Luiz Passos"** (34 subs / 18 nomes) — a ficha tinha as chaves do próprio Luiz, e
  ~15 pessoas reais + lixo de teste grudaram porque as submissões foram preenchidas com
  o **telefone/e-mail do Luiz** (confirmações de evento via proxy, ex. Jantar Carapreta
  ×22). Desmontada: 24 submissões re-resolvidas por nome (**15 religaram a fichas reais
  existentes**, 9 viraram fichas novas needs_review), 3 testes → quarentena. Luiz ficou
  com 7 submissões genuínas.
- **Rita Leão** ÷ Marcelo Leão (telefone do casal compartilhado).
- **Jessica Martins** ÷ Pedro Felipe Duarte (telefone compartilhado).
- **Gustavo Cicutti** ÷ Adriana Stivanin.
- **"teste"** ÷ Rodrigo Casagrande (pessoa real separada; lixo → quarentena).

**🟡 Duplicatas (mesma pessoa em fichas separadas) — 8 fantasmas fundidos:**
Fichas só-nome (de formulários de satisfação/board sem chave forte) fundidas nas ricas:
Gabriel Castelo Branco, João Victor, Lucas Meireles (ghost), Manir (2 ghosts, incl.
telefone com typo), Tamara Andrade, Victor Guelman, Wallace França.

**Causa raiz corrigida no motor (`resolve_person`):**
1. **Match de nome agora por `norm_text`** (antes a fase 2 usava `norm_short` → case/acento
   sensível, criava fantasmas tipo "Wallace frança" ≠ "Wallace França").
2. **Guarda anti-telefone-compartilhado:** se casou SÓ por telefone e o nome novo não
   compartilha nenhum token com o existente → não absorve, cria ficha nova needs_review.
3. Helpers `_merge_person(src,dst)` e `_name_tokens(t)` criados (reutilizáveis).

**Revisão dos needs_review (cruzamento por tokens de nome + decisão do Luiz):**
Helper `_token_overlap(a,b)` criado. Dos 41 needs_review, o cruzamento achou os sósias
por nome (primeiro+sobrenome) e as fichas foram fundidas:
- Auto-seguras (nome incomum / e-mail confirma nome / sem chave conflitante):
  Andre O Batista→Andre Oliveira Batista, Darson Ventura→completo, Hanna Castor (ganhou
  CPF), Izabella Neves, Manir Donato→completo, Rodrigo Cézar Magalhães Rocha,
  Henrique Almada→Henrique Almada Soares Neves, Vitor Kalil→completo.
- Confirmadas pelo Luiz como mesma pessoa: **Lucas Meireles Duarte** (SP+MG+automação360,
  Trip Food = empresa), **Wallace França** (Point Produtora + CPF).
- Confirmado DIFERENTES: Henrique Almada Soares Neves ≠ Alexandre Almada Soares Neves (parentes).
Os ~28 needs_review restantes eram leads esparsos (só-nome, sem nenhum sósia) → flag limpa.

**Resultado FINAL: 420 pessoas reais (+1 quarentena) · 773 submissões · 1.636 insights ·
59 CPFs · 0 duplicatas · 0 fusões erradas · 0 needs_review.** Banco totalmente
reconciliado e auditado.

## Observação
O repositório `mesa` (este, de organização de pensamento) e o produto `MESA` (o Supabase
do app) são coisas distintas que por acaso têm o mesmo nome.

---

# APÊNDICE TÉCNICO (para retomada em sessão nova)

> Tudo abaixo já está APLICADO no Supabase. Serve pra retomar sem reconstruir nada.

## Projeto Supabase
- Projeto: **MESA**, project_id = `hgwjvfgntfpvgdghngtn`, Postgres 17, pgvector 0.8.
- Acesso via MCP Supabase (`execute_sql`, `apply_migration`, `get_advisors`).

## Tabelas da camada CRM (todas com RLS ON, sem política = sem acesso público)
- **`people`** — ficha unificada. Colunas: `id uuid pk`, `full_name`, `primary_email`,
  `primary_phone`, `instagram`, `city`, `birthdate`, `company_name`, `segment`, `role`,
  `monthly_revenue_range`, `profile_id` (FK opcional → profiles), `merge_confidence`
  (`high`|`low_name_only`), `needs_review bool`, `created_at`, `updated_at`.
- **`person_identities`** — chaves da cascata. `kind` IN (`email`,`cpf`,`phone`,
  `instagram`,`name`), `value_norm`, `source`. UNIQUE(`kind`,`value_norm`).
- **`source_submissions`** — ponto de contato cru. `source`,`source_form_id`,
  `source_form_name`,`external_id`,`submitted_at`,`raw_payload jsonb`,`processed_at`.
  UNIQUE(`source`,`external_id`) → idempotência. **raw_payload = array `responses`** do Tally.
- **`person_insights`** — qualitativo. `kind` IN (`about`,`challenge`,`trajectory`,
  `goal`,`lifestyle`,`motivation`,`pain`,`intro_phrase`,`wish`), `text_content`,
  `source` (ex.: `tally:mDyqRZ`). UNIQUE(`person_id`,`source`,`kind`).
  ⚠️ NÃO confundir com a tabela legada `member_insights` (do app, schema diferente).

## Funções (todas com search_path = public, pg_catalog)
- `norm_text(t)` — lower + sem acento + colapsa espaço. **SÓ pra chaves, nunca display.**
- `norm_short(t)` — trim, null se < 2 chars.
- `norm_email / norm_phone(→E.164) / norm_instagram(sem @) / norm_cpf(11 díg, rejeita repetido)`.
- `_tally_ans(p_resp jsonb, p_qid text)` — extrai `answer` por questionId. Recebe o
  array `responses` (NÃO o payload inteiro).
- `resolve_person(p_full_name, p_email, p_cpf, p_phone, p_instagram, p_city,
  p_birthdate, p_company, p_segment, p_role, p_monthly_revenue)` — cascata
  email→cpf→phone→instagram→name; cria ou **enriquece (só campo vazio)**; match por
  nome marca `needs_review`. **USAR PARÂMETROS NOMEADOS**.
- `ingest_tally_confirmacao(p_form_id, p_form_name, p_rows, p_qid_nome,
  p_qid_sobrenome DEFAULT NULL, p_qid_phone DEFAULT NULL, p_qid_email DEFAULT NULL)`
  — **genérico** para confirmações de evento simples, sem insights.

### Ingestores específicos (todos: `p_form_id, p_form_name, p_rows jsonb`)
`p_rows` = array de `{id, submittedAt, responses:[{questionId,answer}]}`.

| Função | Form ID | Insights |
|--------|---------|---------|
| `ingest_tally_newmembers` | `wbvQx1` | motivation, pain, intro_phrase, wish |
| `ingest_tally_conexao` | `mDyqRZ` | about, challenge, trajectory, goal, lifestyle |
| `ingest_tally_interesse` | `mVglxl` | motivation, pain, intro_phrase, wish |
| `ingest_tally_2026` | `RGWxlp` | goal, challenge, pain |
| `ingest_tally_indicacoes` | `VLvZWN` | intro_phrase, about, wish |
| `ingest_tally_onboarding` | `XxeKbO` | goal, pain, challenge, trajectory, about |
| `ingest_tally_advisory_waitlist` | `q4Ozvd` | about, pain, motivation |
| `ingest_tally_board_meeting` | `waMaRX` | trajectory, pain |
| `ingest_tally_board_2602` | `b57a01` | challenge, trajectory |
| `ingest_tally_jantar_outside` | `mOv0Ya` | pain, wish |
| `ingest_tally_ia_imersao` | `nPa8Oe` | pain, wish |
| `ingest_tally_jantar_one` | `w2QzQ9` | challenge, pain, wish |
| `ingest_tally_mesa_ia` | `vGqly4` | pain, challenge, wish |
| `ingest_tally_bedeal` | `dWEORz` | about |
| `ingest_tally_satisfacao_geral` | `wvbJ5d` | intro_phrase, about |
| `ingest_tally_board_satisfacao` | `2E4jqL` | about |
| `ingest_tally_diagnostico_vendas` | `mBqNQA` | pain, wish |
| `ingest_tally_sexta_fire` | `Pd17JP` | — (só identidade + CPF) |
| `ingest_tally_talk_mesa` | `LZWZd1` | — (só identidade + CPF) |
| `ingest_tally_resgate` | `3NKlrN` | motivation |
| `ingest_tally_board_form` | `VL8N8N` | trajectory, pain, challenge |
| `ingest_tally_mentoria` | `mRp12j` | about, trajectory, pain, goal, wish |
| `ingest_tally_mesa_aberta_vaga` | `5Be9AM` | wish |
| `ingest_tally_satisfacao_mesa_ia_evento` | `rjkBV5` | about |
| `ingest_tally_satisfacao_ia_int` | `2EL44j` | about |
| `ingest_tally_imersao_ia` | `jaGkva` | wish |
| `ingest_tally_diagnostico_patricia` | `oboXLb` | — (sem identidade, raw store) |

**Confirmações via genérico:** `wzPQyM` Happy Hour (nome VzRN6M, sob PzMrqB, phone Exj6OB),
`7R4BMZ` Board #3 (nome opcional 4j78gb), e outros forms simples de confirmação.

**Bloqueados (label null bug MCP):** `3xq8e9` (69 sub), `wgE0G1` (23 sub).

## Mapeamento de questionId — forms principais

**Form 1 `wbvQx1` (155 resp):** nome `E5jxJ4`, email `BdJkbQ`, phone `2BqKxj`,
ig `vr7yrv`, cidade `ke86RR`, empresa `GKNdeZ`, seg `Olp5QR`, cargo `VjR5pg` (array),
nascimento `rBNodN`. Qualitativos: motivation `PDM5RV`, pain `E5jQq4`,
intro_phrase `ve8yx0`, wish `K5rlB8` (cobertura parcial — submissões antigas não tinham).

**Form 2 `mDyqRZ` (72 resp):** nome `ZELpdz`, email `VQXE6N`, phone `qD72bY`,
ig `7Lg8dP` (skip se linkedin), CPF `P1LjqP`, nascimento `O4K1Nk`, empresa `EdezOA`,
cargo `raRyZp`, faturamento `2az86g`, seg `xMExWE`.
Qualitativos: about `G9avPQ`, challenge `G9avPO`, trajectory `oeY6jN`, goal `O4K1NM`, lifestyle `WEkvAj`.

**Pd17JP "Sexta Fire" (14 resp, CPF):** nome `R0R90l`+`oyojy1`, email `OzLNzK`,
phone `GzLPzj`, cidade `V0V60a`, CPF `ZNl7AB`, empresa `r6VZ6M`, seg `48Lb8b`,
cargo `jyLVyR`, faturamento_anual `2eL6ep` (MC).

**LZWZd1 "Talk A Mesa" (8 resp, CPF):** nome `Grxv0O`+`OAD10M`, email `PAdj0x`,
phone `VZLE86`, cidade `EPkz02`, CPF `Zdj5l5`, empresa `424Xj5`, seg `jBaDx1`,
cargo `24E8rM`, faturamento_anual `xdXxZk` (MC).

**mRp12j "Mentoria Luiz Passos" (3 resp, muito rico):** nome `o2qMAV`+`GRZdro`,
email `6ZgbbO`, phone `Y41Wz0`, cidade `d9Ox2N`.
Insights: about `O765A8`, trajectory `Ex2QPN`, pain `Pz75Ab`, goal `4KMx2O`, wish `jljQBE`.

Para os demais forms, os question IDs estão na definição das funções no Supabase.

## Como reprocessar uma fonte (idempotente)
`fetch_submissions(formId, limit=50, page=N)` no MCP Tally → passar `data.submissions`
como `p_rows` pra `ingest_tally_*` via `$JSON$...$JSON$::jsonb` no execute_sql.
Re-rodar não duplica. Resposta grande → usar subagente pra não estourar contexto.

## Fase 5 — Tally 100% (✔ executado 2026-05-30)
Os 2 forms bloqueados pelo bug `label:null` do MCP foram resolvidos via **export CSV**
(o Luiz baixou e subiu os arquivos). Ingeridos por SQL direto pelo mesmo `resolve_person`:
- `3xq8e9` Café com o Zema — 69 confirmações (nome+telefone+email)
- `wgE0G1` BOPE — 23 confirmações (nome+telefone+documento→CPF quando válido)
A guarda anti-telefone-compartilhado agiu (ex.: "Gabriel Mota" veio com o telefone do
Leonardo Ramalho → não fundiu, virou ficha própria). 0 duplicatas, 0 fusões erradas.
4 fichas em needs_review (colisões de nome legítimas p/ revisão: Bruno Castro,
Célio Brasil, Gabriel Mota, Matheus Garcia).

**Cobertura Tally agora 100%: 35 formulários com dados ingeridos** (33 via MCP + 2 via CSV);
6 vazios/rascunho; 1 lixo de teste em quarentena (`yPjlA6`).

## Fase 6 — Embeddings / busca semântica (✔ executado 2026-05-30)
Com o dado limpo, geradas embeddings de TODAS as 467 fichas.
- **Modelo:** OpenAI `text-embedding-3-small` (1536d) — escolhido pela qualidade em PT.
  Chave fornecida pelo Luiz, guardada no **Vault** do Supabase (criptografada; rotacionar
  depois por segurança, já que passou pelo chat).
- **Pipeline 100% no banco:** extensão `http` chama a OpenAI direto do Postgres; sem
  serviço externo.

**Criado (RLS ON):**
- `person_embeddings(person_id, content, embedding vector(1536), model)` + índice **HNSW**
  (cosine). 467 vetores.
- `person_document(uuid)` — compõe o "documento" da pessoa (identificação + negócio +
  todos os insights) que vira o embedding.
- `openai_embed(text)` — chama OpenAI via `http`+Vault, devolve `vector`.
- `embed_pending_people(int)` — driver idempotente (só embedda quem ainda não tem vetor).
- `search_people(texto, k)` — **busca semântica** por linguagem natural (similaridade de
  cosseno). Ex.: "reter talentos / formar líderes" → 1º = Gustavo Cicutti, cujo objetivo
  escrito é literalmente isso. Entende significado, não keyword.

**Re-embeddar dado novo:** `SELECT embed_pending_people(30);` em **lotes pequenos** —
a extensão `http` tem teto de ~5s por chamada e estoura em lote grande (a função é
idempotente: só pega quem não tem vetor, é só repetir até `faltam=0`). Trocar modelo =
limpar a tabela e re-rodar. (Alternativa mais rápida p/ backfill grande: script externo
usando a API batch da OpenAI.)

## Estado atual (2026-05-30, pós fase 6 — embeddings)
**467 pessoas reais (+1 quarentena) · 866 submissões · 1.636 insights · 67 CPFs ·
467 embeddings (1536d) · 4 needs_review**
Tally 100%. Busca semântica ativa (`search_people`). Motor de identidade blindado.
Cascata: email → cpf → phone → instagram → name (match de nome por `norm_text`).
Helpers: `_merge_person`, `_name_tokens`, `_token_overlap`, `person_document`, `openai_embed`.

**Próximos passos reais:**
- Fontes não-Tally: Notion, Granola, Zoom, Drive, Gmail, agenda — enriquecer fichas.
- Interface de consulta (usar `search_people` numa tela/chat pro consultor).
- Embeddings por insight (granular) se quiser busca por dor específica.
- RLS legado: 57 tabelas do app MESA sem política (buraco de segurança).
- Revisar as 4 needs_review (colisões de nome — Bruno Castro, Gabriel Mota, etc.).
