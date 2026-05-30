#!/usr/bin/env python3
"""Enriquece text_content dos links tl;dv em person_insights com highlights reais.

Para cada link tl;dv com resumo vazio ("Reunião X (date)."):
- Busca highlights via API tl;dv
- Para boards individuais: constrói resumo focado na pessoa
- Para reuniões coletivas: constrói resumo geral da reunião

Uso:
    export SB_URL="..." SB_KEY="..."
    python3 scripts/update_tldv_summaries.py
"""
import json, os, urllib.request, urllib.parse

SB_KEY   = os.environ["SB_KEY"]
SB_URL   = os.environ["SB_URL"].rstrip("/")
TLDV_KEY = "dd33710b-b0c4-490e-b0f9-6e6d8f989f39"

SKIP_TOPICS = {"itens de ação", "action items", "próximos passos"}


def sb(path, params=None, body=None, method="GET"):
    qs = ("?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)) if params else ""
    req = urllib.request.Request(
        f"{SB_URL}/rest/v1/{path}{qs}",
        data=json.dumps(body).encode() if body else None,
        method=method,
        headers={
            "apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY,
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
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
            return json.loads(r.read()).get("data", [])
    except Exception:
        return []


def build_summary(highlights, title, date_str, person_name=None):
    """Monta texto rico a partir dos highlights, agrupado por tópico."""
    if not highlights:
        return None

    # Agrupa por tópico, exclui ação
    grouped = {}
    for h in highlights:
        topic = h.get("topic", {}).get("title", "Geral")
        if any(skip in topic.lower() for skip in SKIP_TOPICS):
            continue
        grouped.setdefault(topic, []).append(h["text"])

    if not grouped:
        return None

    lines = [f'Board "{title}" ({date_str}).']
    for topic, items in list(grouped.items())[:6]:  # máx 6 tópicos
        bullets = " | ".join(items[:3])  # máx 3 bullets por tópico
        lines.append(f"[{topic}] {bullets}")

    return "\n".join(lines)


def main():
    # Busca todos os links tl;dv com resumo curto (< 80 chars)
    links = sb("person_insights", {
        "kind":   "eq.meeting",
        "source": "like.tldv:*",
        "select": "id,person_id,source,text_content",
    })
    short = [l for l in links if len(l.get("text_content", "")) < 80]
    print(f"# {len(short)} links tl;dv com resumo vazio\n")

    # Agrupa por meeting_id para buscar highlights uma vez por meeting
    by_meeting = {}
    for lnk in short:
        mid = lnk["source"].split("tldv:", 1)[1]
        by_meeting.setdefault(mid, []).append(lnk)

    updated = 0
    for mid, lnk_list in by_meeting.items():
        # Metadados da reunião
        tx = sb("granola_transcripts", {
            "meeting_id": f"eq.{mid}",
            "select": "title,meeting_date",
        })
        if not tx:
            continue
        title    = tx[0]["title"]
        date_str = (tx[0].get("meeting_date") or "")[:10]

        highlights = get_highlights(mid)
        if not highlights:
            print(f"  — {title[:50]} (sem highlights)")
            continue

        summary = build_summary(highlights, title, date_str)
        if not summary:
            print(f"  — {title[:50]} (highlights sem tópicos úteis)")
            continue

        # Atualiza todos os links desta reunião com o mesmo resumo
        ids = [l["id"] for l in lnk_list]
        for lid in ids:
            sb("person_insights", {"id": f"eq.{lid}"},
               body={"text_content": summary}, method="PATCH")

        updated += len(ids)
        print(f"  ✓ {title[:50]} → {len(ids)} link(s) atualizados")

    print(f"\n# Total: {updated} links enriquecidos")


if __name__ == "__main__":
    main()
