#!/usr/bin/env python3
"""Buscador do motor de leads MESA — consulta o CRM pelo terminal.

Busca por palavras soltas (ex: "césar" acha "César Vasconcelos Canal").
Mostra: dados da pessoa, identidades, insights e reuniões (Granola + tl;dv).
Com --transcricao, despeja o texto verbatim das reuniões encontradas.

Uso:
    export SB_URL="https://hgwjvfgntfpvgdghngtn.supabase.co"
    export SB_KEY="<service_role key>"

    python3 scripts/buscar.py "césar"
    python3 scripts/buscar.py "hanna" --transcricao
    python3 scripts/buscar.py "lucas meireles"
"""
import json, os, sys, urllib.request, urllib.parse

SB_KEY = os.environ["SB_KEY"]
SB_URL = os.environ["SB_URL"].rstrip("/")


def api(path, params):
    qs = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    req = urllib.request.Request(f"{SB_URL}/rest/v1/{path}?{qs}", headers={
        "apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY,
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def search_people(query):
    """Busca por todas as palavras do query no nome (AND implícito)."""
    words = query.lower().split()

    # 1. Busca direta no full_name por cada palavra
    candidates = {}
    for word in words:
        rows = api("people", {
            "full_name": f"ilike.*{word}*",
            "select": "id,full_name,primary_email,company_name,role,segment,"
                      "monthly_revenue_range,birthdate,needs_review",
            "order": "full_name",
            "limit": "100",
        })
        for r in rows:
            candidates.setdefault(r["id"], (r, 0))
            _, count = candidates[r["id"]]
            candidates[r["id"]] = (r, count + 1)

    # 2. Busca em person_identities kind=name (apanha variações e apelidos)
    for word in words:
        id_rows = api("person_identities", {
            "kind": "eq.name",
            "value_norm": f"ilike.*{word}*",
            "select": "person_id",
            "limit": "100",
        })
        for r in id_rows:
            pid = r["person_id"]
            if pid not in candidates:
                # Busca dados completos da pessoa
                people = api("people", {
                    "id": f"eq.{pid}",
                    "select": "id,full_name,primary_email,company_name,role,segment,"
                              "monthly_revenue_range,birthdate,needs_review",
                })
                if people:
                    candidates[pid] = (people[0], 0)
            _, count = candidates.get(pid, (None, 0))
            if candidates.get(pid):
                p, c = candidates[pid]
                candidates[pid] = (p, c + 1)

    # Filtra quem tem todas as palavras (count >= len(words))
    matched = [p for p, count in candidates.values() if count >= len(words)]

    # Deduplica e ordena por nome
    seen = set()
    result = []
    for p in sorted(matched, key=lambda x: x["full_name"]):
        if p["id"] not in seen:
            seen.add(p["id"])
            result.append(p)
    return result


def print_person(p, show_tx=False):
    flag = "  ⚠ needs_review" if p.get("needs_review") else ""
    print(f"\n● {p['full_name']}{flag}")
    for label, key in [("email", "primary_email"), ("empresa", "company_name"),
                       ("cargo", "role"), ("segmento", "segment"),
                       ("faturamento", "monthly_revenue_range"), ("nascimento", "birthdate")]:
        if p.get(key):
            print(f"    {label:12} {p[key]}")

    ids = api("person_identities", {
        "person_id": f"eq.{p['id']}", "select": "kind,value_norm", "order": "kind",
    })
    if ids:
        grouped = {}
        for i in ids:
            grouped.setdefault(i["kind"], []).append(i["value_norm"])
        print("    identidades:")
        for kind, vals in grouped.items():
            print(f"      {kind:10} {', '.join(vals)}")

    insights = api("person_insights", {
        "person_id": f"eq.{p['id']}",
        "select": "kind,text_content,source", "order": "created_at",
    })
    non_meet = [i for i in insights if i["kind"] != "meeting"]
    meets    = [i for i in insights if i["kind"] == "meeting"]

    if non_meet:
        print("    insights:")
        for i in non_meet:
            txt = i["text_content"].replace("\n", " ")
            if len(txt) > 200:
                txt = txt[:200] + "…"
            print(f"      [{i['kind']}] {txt}")

    if meets:
        print(f"    reuniões ({len(meets)}):")
        for m in meets:
            src = m["source"]
            # Suporta granola: e tldv:
            if ":" in src:
                mid = src.split(":", 1)[1]
            else:
                mid = src
            tx = api("granola_transcripts", {
                "meeting_id": f"eq.{mid}",
                "select": "title,meeting_date,char_count,source,transcript",
            })
            if tx:
                t = tx[0]
                date   = (t.get("meeting_date") or "")[:10]
                source = t.get("source", "")
                tag    = f"[{source}]" if source else ""
                print(f"      • {date}  {t['title']}  ({t['char_count']:,} chars) {tag}")
                summ = m["text_content"].replace("\n", " ")
                if len(summ) > 180:
                    summ = summ[:180] + "…"
                print(f"        resumo: {summ}")
                if show_tx:
                    print(f"        {'-'*60}")
                    print(t["transcript"])
                    print(f"        {'-'*60}")
            else:
                print(f"      • (sem transcrição) {mid}")


def main():
    args    = [a for a in sys.argv[1:] if not a.startswith("--")]
    show_tx = "--transcricao" in sys.argv
    if not args:
        print("uso: buscar.py <nome ou palavra> [--transcricao]")
        sys.exit(1)
    query = " ".join(args)

    people = search_people(query)
    if not people:
        print(f"Nenhuma pessoa encontrada para '{query}'.")
        return

    print(f"\n{'='*70}\n{len(people)} pessoa(s) para '{query}'\n{'='*70}")
    for p in people:
        print_person(p, show_tx)
    print()


if __name__ == "__main__":
    main()
