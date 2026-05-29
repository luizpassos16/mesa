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

## Aprendizados / próximos passos (atualizados)
- **Telefone compartilhado** ainda funde casal/sócios silenciosamente — CPF resolve a
  maioria dos casos novos, mas falta a regra "nomes muito diferentes → revisar".
- **Qualitativo do form 1** (`wbvQx1`) ainda não foi extraído — está no `raw_payload`,
  dá pra rodar o mesmo padrão de limpeza.
- **Escala:** o padrão (mapeamento de questionId → ingestor idempotente) já serve pras
  outras ~40 fontes do Tally. Próximo passo natural: confirmações de evento (muito
  volume) pra cruzar presença com perfil.
- **RLS legado:** 57 tabelas antigas seguem abertas (ERROs no advisor) — tarefa separada,
  recomendo priorizar antes de uso real.
- **member_embeddings** (pgvector instalado): com o qualitativo populado, dá pra gerar
  embeddings da ficha pra busca semântica.

## Observação
O repositório `mesa` (este, de organização de pensamento) e o produto `MESA` (o Supabase
do app) são coisas distintas que por acaso têm o mesmo nome.
