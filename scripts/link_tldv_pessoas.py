#!/usr/bin/env python3
"""Liga transcrições tl;dv às pessoas via speaker name + invitee email.

Para cada transcrição tl;dv no Supabase:
1. Extrai speakers únicos do texto (linhas: [MM:SS] Nome: texto)
2. Busca emails dos participantes via API tl;dv
3. Faz match em person_identities (kind=name ou kind=email)
4. Cria person_insights(kind='meeting', source='tldv:{id}')

Uso:
    export SB_URL="..." SB_KEY="..."
    python3 scripts/link_tldv_pessoas.py
"""
import json, os, re, urllib.request, urllib.parse

SB_KEY   = os.environ["SB_KEY"]
SB_URL   = os.environ["SB_URL"].rstrip("/")
TLDV_KEY = "dd33710b-b0c4-490e-b0f9-6e6d8f989f39"

LUIZ = {"luiz gustavo passos", "luiz gustavo", "luiz passos"}


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


def tldv_invitees(meeting_id):
    """Retorna lista de emails dos participantes via tl;dv API."""
    url = f"https://pasta.tldv.io/v1alpha1/meetings/{meeting_id}"
    req = urllib.request.Request(url, headers={
        "x-api-key": TLDV_KEY, "User-Agent": "curl/7.81.0", "Accept": "*/*"
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read())
            invitees = d.get("invitees", [])
            return [i["email"].lower().strip() for i in invitees if i.get("email")]
    except Exception:
        return []


def extract_speakers(transcript_text):
    """Extrai nomes únicos de speakers do texto formatado [MM:SS] Nome: ..."""
    names = set()
    for m in re.finditer(r"^\[\d{2}:\d{2}\] ([^:]+):", transcript_text, re.MULTILINE):
        name = m.group(1).strip()
        if name.lower() not in LUIZ and len(name) > 2:
            names.add(name)
    return names


def find_person_by_name(name):
    """Busca person_id via person_identities kind=name."""
    rows = sb("person_identities", {
        "kind": "eq.name",
        "value_norm": f"ilike.*{name}*",
        "select": "person_id",
        "limit": "1",
    })
    return rows[0]["person_id"] if rows else None


def find_person_by_email(email):
    """Busca person_id via person_identities kind=email."""
    rows = sb("person_identities", {
        "kind": "eq.email",
        "value_norm": f"eq.{email.lower()}",
        "select": "person_id",
        "limit": "1",
    })
    return rows[0]["person_id"] if rows else None


def insight_exists(person_id, meeting_id):
    rows = sb("person_insights", {
        "person_id": f"eq.{person_id}",
        "source": f"eq.tldv:{meeting_id}",
        "kind": "eq.meeting",
        "select": "id",
        "limit": "1",
    })
    return len(rows) > 0


def create_insight(person_id, meeting_id, title, date):
    date_str = date[:10] if date else ""
    text = f'Reunião "{title}" ({date_str}).'
    sb("person_insights", body=[{
        "person_id": person_id,
        "kind": "meeting",
        "source": f"tldv:{meeting_id}",
        "text_content": text,
    }], method="POST")


def main():
    meetings = sb("granola_transcripts", {
        "source": "eq.tldv",
        "select": "meeting_id,title,meeting_date,transcript,participants",
        "order": "meeting_date",
    })
    print(f"# {len(meetings)} transcrições tl;dv para processar\n")

    total_links = 0

    for m in meetings:
        mid   = m["meeting_id"]
        title = m["title"]
        date  = m.get("meeting_date", "")
        text  = m.get("transcript", "") or ""

        # 1. Speakers do texto
        speakers  = extract_speakers(text)
        # 2. Emails dos participantes via API
        emails    = tldv_invitees(mid)

        linked = set()

        # Via email (mais confiável)
        for email in emails:
            pid = find_person_by_email(email)
            if pid and pid not in linked:
                if not insight_exists(pid, mid):
                    create_insight(pid, mid, title, date)
                linked.add(pid)

        # Via nome de speaker
        for name in speakers:
            pid = find_person_by_name(name)
            if pid and pid not in linked:
                if not insight_exists(pid, mid):
                    create_insight(pid, mid, title, date)
                linked.add(pid)

        if linked:
            total_links += len(linked)
            print(f"  ✓ {title[:50]}")
            print(f"    → {len(linked)} pessoa(s) linkadas")
        else:
            print(f"  — {title[:50]} (nenhuma pessoa matched)")

    print(f"\n# Total: {total_links} links criados")


if __name__ == "__main__":
    main()
