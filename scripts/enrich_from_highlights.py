#!/usr/bin/env python3
"""Enriquece perfis de membros com insights extraídos dos highlights tl;dv.

Para cada board individual no Supabase (source=tldv):
1. Busca highlights via API tl;dv (já processados por IA)
2. Agrupa por tópico e classifica em kinds do CRM (pain/goal/challenge/about)
3. Cria person_insights para a pessoa linkada àquela reunião

Uso:
    export SB_URL="..." SB_KEY="..."
    python3 scripts/enrich_from_highlights.py
"""
import json, os, re, urllib.request, urllib.parse

SB_KEY   = os.environ["SB_KEY"]
SB_URL   = os.environ["SB_URL"].rstrip("/")
TLDV_KEY = "dd33710b-b0c4-490e-b0f9-6e6d8f989f39"

# Mapeamento de tópicos tl;dv → kind do CRM
TOPIC_KIND = {
    "desafios operacionais":           "pain",
    "questões pessoais e bem-estar":   "pain",
    "estratégia de expansão":          "goal",
    "objetivos":                       "goal",
    "metas":                           "goal",
    "resultados":                      "goal",
    "gestão de pessoas e desenvolvimento": "challenge",
    "recrutamento":                    "challenge",
    "processos":                       "challenge",
    "estrutura organizacional":        "about",
    "modelo de negócio":               "about",
    "trajetória":                      "trajectory",
    "comunicação e relacionamento":    "about",
    "tecnologia":                      "challenge",
    "financeiro":                      "pain",
    "vendas":                          "goal",
    "marketing":                       "goal",
}

# Boards individuais: apenas meetings com 1 pessoa linkada (diagnóstico 1:1)
BOARD_PATTERN = re.compile(r"board diagnóstico", re.IGNORECASE)


def sb(path, params=None, body=None, method="GET"):
    qs = ("?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)) if params else ""
    req = urllib.request.Request(
        f"{SB_URL}/rest/v1/{path}{qs}",
        data=json.dumps(body).encode() if body else None,
        method=method,
        headers={
            "apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY,
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        return json.loads(raw) if raw else []


def get_highlights(meeting_id):
    url = f"https://pasta.tldv.io/v1alpha1/meetings/{meeting_id}/highlights"
    req = urllib.request.Request(url, headers={
        "x-api-key": TLDV_KEY, "User-Agent": "curl/7.81.0", "Accept": "*/*"
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read())
            return d.get("data", [])
    except Exception as e:
        print(f"    (highlights error: {e})")
        return []


def classify_kind(topic_title):
    t = topic_title.lower()
    for key, kind in TOPIC_KIND.items():
        if key in t:
            return kind
    return None  # skip unknown topics


def insight_exists(person_id, source_tag):
    rows = sb("person_insights", {
        "person_id": f"eq.{person_id}",
        "source":    f"eq.{source_tag}",
        "kind":      f"neq.meeting",
        "select":    "id",
        "limit":     "1",
    })
    return len(rows) > 0


def create_insights(person_id, meeting_id, grouped):
    """Insere um insight por tópico agrupado."""
    rows = []
    for kind, items in grouped.items():
        text = " | ".join(items)
        rows.append({
            "person_id":    person_id,
            "kind":         kind,
            "source":       f"tldv:{meeting_id}",
            "text_content": text,
        })
    if rows:
        sb("person_insights", body=rows, method="POST")
    return len(rows)


def main():
    # Busca todos os meetings tl;dv que têm pelo menos 1 pessoa linkada
    links = sb("person_insights", {
        "kind":   "eq.meeting",
        "source": "like.tldv:*",
        "select": "person_id,source",
    })

    # Agrupa: meeting_id → [person_ids]
    meeting_persons = {}
    for lnk in links:
        mid = lnk["source"].split("tldv:", 1)[1]
        meeting_persons.setdefault(mid, []).append(lnk["person_id"])

    # Pega metadados dos meetings
    meetings = sb("granola_transcripts", {
        "source": "eq.tldv",
        "select": "meeting_id,title",
    })
    meeting_meta = {m["meeting_id"]: m["title"] for m in meetings}

    print(f"# {len(meeting_persons)} meetings tl;dv com pessoas linkadas\n")
    total_insights = 0

    for mid, person_ids in sorted(meeting_persons.items()):
        title = meeting_meta.get(mid, mid)

        # Só processa boards individuais (1 pessoa) para não misturar insights
        if len(person_ids) != 1:
            print(f"  — {title[:55]} ({len(person_ids)} pessoas, pulando)")
            continue

        person_id = person_ids[0]

        # Evita reprocessar
        if insight_exists(person_id, f"tldv:{mid}"):
            print(f"  ✓ {title[:55]} (já enriquecido)")
            continue

        highlights = get_highlights(mid)
        if not highlights:
            print(f"  — {title[:55]} (sem highlights)")
            continue

        # Agrupa highlights por kind, excluindo "Itens de Ação"
        grouped = {}
        for h in highlights:
            topic  = h.get("topic", {}).get("title", "")
            if "ação" in topic.lower() or "action" in topic.lower():
                continue
            kind = classify_kind(topic)
            if not kind:
                continue
            grouped.setdefault(kind, []).append(h["text"])

        if not grouped:
            print(f"  — {title[:55]} (highlights sem tópicos mapeáveis)")
            continue

        n = create_insights(person_id, mid, grouped)
        total_insights += n
        kinds_str = ", ".join(f"{k}({len(v)})" for k, v in grouped.items())
        print(f"  ✓ {title[:55]}")
        print(f"    → {n} insights: {kinds_str}")

    print(f"\n# Total: {total_insights} insights criados")


if __name__ == "__main__":
    main()
