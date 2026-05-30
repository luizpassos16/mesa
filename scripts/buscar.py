#!/usr/bin/env python3
"""Buscador do motor de leads MESA — consulta o CRM pelo terminal.

Dado um nome (ou parte dele), mostra: dados da pessoa, todas as identidades,
insights (about/challenge/goal/...) e as reuniões Granola em que participou.
Com --transcricao, despeja a transcrição verbatim das reuniões encontradas.

Uso:
    export SB_URL="https://hgwjvfgntfpvgdghngtn.supabase.co"
    export SB_KEY="<service_role key>"

    python3 scripts/buscar.py "victor gontijo"
    python3 scripts/buscar.py "hanna" --transcricao
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

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    show_tx = "--transcricao" in sys.argv
    if not args:
        print("uso: buscar.py <nome> [--transcricao]")
        sys.exit(1)
    query = " ".join(args)

    people = api("people", {
        "full_name": f"ilike.*{query}*",
        "select": "id,full_name,primary_email,company_name,role,segment,"
                  "monthly_revenue_range,birthdate,needs_review",
        "order": "full_name",
    })
    if not people:
        print(f"Nenhuma pessoa encontrada para '{query}'.")
        return

    print(f"\n{'='*70}\n{len(people)} pessoa(s) para '{query}'\n{'='*70}")
    for p in people:
        flag = "  ⚠ needs_review" if p.get("needs_review") else ""
        print(f"\n● {p['full_name']}{flag}")
        for label, key in [("email","primary_email"),("empresa","company_name"),
                           ("cargo","role"),("segmento","segment"),
                           ("faturamento","monthly_revenue_range"),
                           ("nascimento","birthdate")]:
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
                if len(txt) > 200: txt = txt[:200] + "…"
                print(f"      [{i['kind']}] {txt}")
        if meets:
            print(f"    reuniões ({len(meets)}):")
            for m in meets:
                mid = m["source"].split("granola:")[-1]
                tx = api("granola_transcripts", {
                    "meeting_id": f"eq.{mid}",
                    "select": "title,meeting_date,char_count,transcript",
                })
                if tx:
                    t = tx[0]
                    date = (t.get("meeting_date") or "")[:10]
                    print(f"      • {date}  {t['title']}  ({t['char_count']:,} chars)")
                    summ = m["text_content"].replace("\n", " ")
                    if len(summ) > 180: summ = summ[:180] + "…"
                    print(f"        resumo: {summ}")
                    if show_tx:
                        print(f"        {'-'*60}")
                        print(t["transcript"])
                        print(f"        {'-'*60}")
                else:
                    print(f"      • (sem transcrição) {mid}")
    print()

if __name__ == "__main__":
    main()
