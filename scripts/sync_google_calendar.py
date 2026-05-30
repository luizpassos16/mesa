#!/usr/bin/env python3
"""Sincroniza eventos do Google Calendar com o CRM da Mesa.

Para cada evento com attendees externos:
1. Busca a pessoa em person_identities via email
2. Cria source_submission (fonte=google_calendar)
3. Cria person_insights (kind=meeting) com resumo do evento

Uso:
    export SB_URL="..." SB_KEY="..."
    # Primeiro exporta os eventos via MCP e salva em /tmp/calendar_attendees.json
    python3 scripts/sync_google_calendar.py [--arquivo /tmp/calendar_attendees.json]

Formato esperado do JSON:
[{"id": "...", "summary": "...", "start": "2026-...", "attendees": ["email@..."]}]
"""
import json, os, sys, urllib.request, urllib.parse

SB_KEY = os.environ["SB_KEY"]
SB_URL = os.environ["SB_URL"].rstrip("/")
LUIZ   = "lgcmp44@gmail.com"

arquivo = "/tmp/calendar_attendees.json"
for i, arg in enumerate(sys.argv):
    if arg == "--arquivo" and i + 1 < len(sys.argv):
        arquivo = sys.argv[i + 1]


def sb(path, params=None, body=None, method="GET"):
    qs = ("?" + urllib.parse.urlencode(params or {})) if params else ""
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


def find_person_by_email(email):
    rows = sb("person_identities", {
        "kind":       "eq.email",
        "value_norm": f"eq.{email.lower()}",
        "select":     "person_id",
        "limit":      "1",
    })
    return rows[0]["person_id"] if rows else None


def submission_exists(external_id):
    rows = sb("source_submissions", {
        "external_id": f"eq.{external_id}",
        "select":      "id",
        "limit":       "1",
    })
    return len(rows) > 0


def insight_exists(person_id, source):
    rows = sb("person_insights", {
        "person_id": f"eq.{person_id}",
        "source":    f"eq.{source}",
        "kind":      "eq.meeting",
        "select":    "id",
        "limit":     "1",
    })
    return len(rows) > 0


def create_submission(event, person_id):
    date_str = (event.get("start") or "")[:10]
    sb("source_submissions", body=[{
        "person_id":       person_id,
        "source":          "google_calendar",
        "source_form_id":  event["id"],
        "source_form_name": event.get("summary", "(sem título)"),
        "external_id":     f"{event['id']}_{person_id}",
        "submitted_at":    event.get("start"),
        "raw_payload":     event,
    }], method="POST")


def create_insight(person_id, event):
    date_str = (event.get("start") or "")[:10]
    title    = event.get("summary", "(sem título)")
    source   = f"google_calendar:{event['id']}"
    text     = f'Evento "{title}" ({date_str}). Participou como convidado na agenda do Luiz.'
    sb("person_insights", body=[{
        "person_id":    person_id,
        "kind":         "meeting",
        "source":       source,
        "text_content": text,
    }], method="POST")


def main():
    with open(arquivo) as f:
        events = json.load(f)

    print(f"# {len(events)} eventos para processar\n")

    total_links = 0
    total_skipped = 0

    for ev in events:
        matched = []
        for email in ev.get("attendees", []):
            if email == LUIZ:
                continue
            pid = find_person_by_email(email)
            if pid:
                matched.append((email, pid))

        if not matched:
            total_skipped += 1
            continue

        title    = ev.get("summary", "(sem título)")
        date_str = (ev.get("start") or "")[:10]
        print(f"  ✓ {date_str}  {title[:45]}")

        for email, pid in matched:
            source = f"google_calendar:{ev['id']}"
            if not insight_exists(pid, source):
                create_insight(pid, ev)
                total_links += 1
                print(f"    → {email}")

    print(f"\n# {total_links} links criados | {total_skipped} eventos sem match no CRM")


if __name__ == "__main__":
    main()
