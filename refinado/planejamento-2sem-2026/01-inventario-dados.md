# 01 — Inventário de dados da MESA

> Mapa das fontes que alimentam (ou vão alimentar) o sistema de dados da MESA. Fase 1 do planejamento.
> Levantado em 27/05/2026 via integrações conectadas.

## Fontes ativas hoje

### Granola (reuniões gravadas)
- Conta conectada: `lgcmp44@gmail.com`.
- **29 reuniões** nos últimos 30 dias (24 de negócio + 4 terapia + 1 setup técnico).
- Conteúdo: summary + notas + transcrição por reunião.
- Cobertura: estratégia de produto, precificação, parcerias, boards, eventos.
- **Maior reservatório de "como o Luiz pensa" e das decisões em andamento.**

### Tally (formulários)
- Workspace único: `nrOd7l`.
- **43 formulários**, agrupáveis em:
  - *Aquisição/membros:* Novos Membros (155), Interesse (71), Conexão entre Membros (72), Banco de Indicações (35), Onboarding (12).
  - *Produto IA:* Mesa Aberta·IA (vaga + satisfação), "Dia 21 MESA #ia" (16), IA na Prática (17), IA + Intencionalidade (7).
  - *Board:* Lista de Espera Advisory Board (15), satisfação Board #2/#3.
  - *Eventos/satisfação:* Sexta Fire, jantares, Experience, "O que você precisa para 2026" (27).
- **Captura estruturada de perfil, dores e intenção.** Ressalva: há respostas-teste/lixo a limpar antes de usar como métrica dura.

### Google Drive (documentos e decks)
- Drive compartilhado da Mesa.
- Decks institucionais e de venda: três pilares, Board 2026 / Advisory Board / PRINCIPAL, Experience 2026, ciclo março, slides de venda Turma 2.
- Briefings: `briefing_setor_restaurantes_bh_hanna_maio2026.pdf` (vertical Soluções/restaurantes).
- **Repositório do posicionamento, ofertas e preços.**

### Notion
- Base de dados atual consultada pelo formulário inteligente (origem dos dados hoje).

### Lovable (experimento descartado)
- Usado para prototipar o formulário inteligente, mas **não vingou** — hoje quase não é usado. A direção é **infra própria** (banco/API próprios) para controle de dados. *Ferramenta de captura atual a confirmar.*

## Fontes a integrar / validar

### tl;dv
- Citado como fonte de gravação de reuniões. A integração de gravações disponível (Zoom/recordings) retornou **0 registros** no período 27/abr–27/mai — **acesso a validar** (pode estar em outra conta/integração).

### WhatsApp (visão futura)
- Agente que varre conversas e extrai informação para o banco. Ainda não implementado.

### Instagram (`@amesa.mg`)
- Canal de aquisição dominante (puxa leads junto com indicação).
- Não acessível por fetch público (403) — posicionamento extraído dos decks.

## Camada de identidade (chave do sistema)

Cada pessoa no banco deve ser identificável e unificável por:
- **CPF**
- **WhatsApp**
- **E-mail**

Objetivo: uma única "pasta" por empresário, consolidando tudo que vem de todas as fontes acima, mesmo com homônimos.

## Lacunas de dado identificadas
- **tl;dv:** acesso programático não confirmado.
- **WhatsApp:** captura ainda manual/inexistente.
- **Higienização:** Tally tem respostas-teste; contagens exatas de bases grandes (Novos Membros, Conexão) ainda parciais.
- **Unificação:** hoje os dados estão em silos (Granola, Tally, Drive, Notion) — a "pasta por pessoa" ainda não existe de forma unificada. **Este é o gargalo central do sistema de dados.**
