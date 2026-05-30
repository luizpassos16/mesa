#!/usr/bin/env python3
"""Carrega transcrições tl;dv para a tabela granola_transcripts (source='tldv') via REST Supabase.

Uso:
    export SB_URL="https://hgwjvfgntfpvgdghngtn.supabase.co"
    export SB_KEY="<service_role key>"
    python3 scripts/load_tldv_transcripts.py

Busca as transcrições direto da API tl;dv, converte para texto legível e faz upsert.
"""
import json, os, urllib.request, urllib.parse, sys

SB_KEY  = os.environ["SB_KEY"]
SB_URL  = os.environ["SB_URL"].rstrip("/")
TLDV_KEY = "dd33710b-b0c4-490e-b0f9-6e6d8f989f39"
ENDPOINT = SB_URL + "/rest/v1/granola_transcripts"

# Priority meetings: boards + sessões individuais dos membros Turma 1
MEETINGS = [
    # --- Boards individuais (Turma 1) ---
    ("69b7fed7e108b900136af62d", "César: Board - A Mesa",                    "2026-03-16T13:00:00-03:00", "César Canal"),
    ("69b95797df37320013d2a758", "Rodrigo: Board - A Mesa",                   "2026-03-17T13:31:00-03:00", "Rodrigo Rocha"),
    ("69b2aac74ddb450012bb2096", "Tiago: Board - A Mesa",                     "2026-03-12T12:00:00-03:00", "Tiago Mota"),
    ("69bc3500771a48001353554e", "Lucas Meireles: Board - A Mesa",            "2026-03-19T17:40:00-03:00", "Lucas Meireles"),
    ("69bc63c3c5ff720013461c45", "Giovanni: Board - A Mesa",                  "2026-03-19T21:00:00-03:00", "Giovanni Naddeo"),
    ("69b40a635278560013577dab", "Igor: Board - A Mesa",                      "2026-03-13T13:00:00-03:00", "Igor Della Croce"),
    ("698f20641bcf5d0012a33af8", "Hanna: Board - A Mesa",                     "2026-02-13T13:00:00-03:00", "Hanna Castor"),
    ("69bc4eaec1f67b0013e5d3b5", "Onboarding João - A Mesa",                  "2026-03-19T19:30:00-03:00", "João Victor Pinheiro Silva"),
    ("69960c3765208800136465e7", "Cassiano: Board - A Mesa",                  "2026-02-18T19:00:00-03:00", "Cassiano"),
    ("698f125160ce960013096afd", "Marcus Prazeres: Board - A Mesa",           "2026-02-13T12:00:00-03:00", "Marcus Prazeres"),
    ("698dc0d3ecdf0e00130112af", "Tiago: Board #1 - A Mesa",                  "2026-02-12T12:00:00-03:00", "Tiago Mota"),
    ("698e152886c6560014c0081c", "Lucas: Board #1 - A Mesa",                  "2026-02-12T18:00:00-03:00", "Lucas Meireles"),
    ("69bc2b9e06969c00138cd854", "Lucas Meireles: Board - A Mesa (v2)",       "2026-03-19T17:00:00-03:00", "Lucas Meireles"),
    # --- Boards coletivos ---
    ("69b1e5d4e108b900136a7861", "Encontro de boas-vindas - Board A Mesa T1", "2026-03-11T22:00:00-03:00", "Turma 1"),
    ("69d81d6312f6dd00136dcc5d", "Board Meeting #2 - A Mesa Turma 1",         "2026-04-09T21:42:00-03:00", "Turma 1"),
    ("69debc278343c3001364d36a", "Board Meeting #2.5 Rodrigo - A Mesa",       "2026-04-14T22:13:00-03:00", "Rodrigo Rocha"),
    ("69fd0d1467d9840014a1fa95", "Board Meeting #3 - A Mesa Turma 1",         "2026-05-07T22:07:00-03:00", "Turma 1"),
    ("69e92a46383a4f0013074d36", "Board Turma 1 — Eduardo Jones One:One",     "2026-04-22T20:06:00-03:00", "Eduardo Jones"),
    # --- Sessões estratégicas ---
    ("69fb42610f3f8300130d512e", "Sessão Estratégica — Wallace França",       "2026-05-06T13:30:00-03:00", "Wallace França"),
    ("69d65e8822f9190013a430db", "One a One — Giovanni / MESA",               "2026-04-08T13:56:00-03:00", "Giovanni Naddeo"),
    ("69d55508b1983400137df343", "Reunião Rodrigo Rocha",                      "2026-04-07T19:03:00-03:00", "Rodrigo Rocha"),
]


def fmt_time(seconds):
    m, s = divmod(int(seconds), 60)
    return f"[{m:02d}:{s:02d}]"


def fetch_tldv_transcript(meeting_id):
    url = f"https://pasta.tldv.io/v1alpha1/meetings/{meeting_id}/transcript"
    req = urllib.request.Request(url, headers={
        "x-api-key": TLDV_KEY,
        "User-Agent": "curl/7.81.0",
        "Accept": "*/*",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"(err: {e})", end=" ")
        return None


def convert_to_text(data):
    if not data:
        return ""
    entries = data if isinstance(data, list) else data.get("data", [])
    lines = []
    for e in entries:
        t = fmt_time(e.get("startTime", 0))
        speaker = e.get("speaker", "?")
        text = e.get("text", "").strip()
        if text:
            lines.append(f"{t} {speaker}: {text}")
    return "\n".join(lines)


def upsert(meeting_id, title, date, transcript, participants):
    body = json.dumps([{
        "meeting_id": meeting_id,
        "title": title,
        "meeting_date": date,
        "transcript": transcript,
        "source": "tldv",
        "participants": participants,
    }]).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=body, method="POST", headers={
        "apikey": SB_KEY,
        "Authorization": "Bearer " + SB_KEY,
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        rep = json.loads(r.read())
    stored = rep[0]["char_count"] if rep else -1
    return stored


def main():
    ok, skip, err = 0, 0, 0
    for meeting_id, title, date, participants in MEETINGS:
        meeting_id = meeting_id.strip()
        print(f"→ {meeting_id[:8]}  {title[:50]}", end=" ... ", flush=True)
        raw = fetch_tldv_transcript(meeting_id)
        if not raw:
            print("SKIP (API retornou vazio)")
            skip += 1
            continue
        text = convert_to_text(raw)
        if not text:
            print("SKIP (transcrição vazia)")
            skip += 1
            continue
        try:
            stored = upsert(meeting_id, title, date, text, participants)
            ok += 1
            print(f"OK ({len(text):,} chars → gravado {stored:,})")
        except Exception as e:
            err += 1
            print(f"ERRO: {str(e)[:100]}")
    print(f"\n# Resultado: {ok} OK | {skip} skip | {err} erros")


if __name__ == "__main__":
    main()
