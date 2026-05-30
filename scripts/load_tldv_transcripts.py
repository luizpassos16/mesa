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

# Todas as reuniões Mesa relevantes
MEETINGS = [
    # --- Boards individuais — 1ª rodada (fev) ---
    ("698dc0d3ecdf0e00130112af", "Tiago Mota: Board Diagnóstico #1 - A Mesa",    "2026-02-12T12:00:00-03:00", "Tiago Mota"),
    ("698e152886c6560014c0081c", "Lucas Meireles: Board Diagnóstico #1 - A Mesa","2026-02-12T18:00:00-03:00", "Lucas Meireles"),
    ("698f20641bcf5d0012a33af8", "Hanna Castor: Board Diagnóstico #1 - A Mesa",  "2026-02-13T13:00:00-03:00", "Hanna Castor"),
    ("698f125160ce960013096afd", "Marcus Prazeres: Board Diagnóstico #1 - A Mesa","2026-02-13T12:00:00-03:00", "Marcus Prazeres"),
    ("69960c3765208800136465e7", "Cassiano: Board Diagnóstico #1 - A Mesa",       "2026-02-18T19:00:00-03:00", "Cassiano"),
    # --- Boards individuais — 2ª rodada (mar) ---
    ("69b01a71e108b900136a373d", "Wallace França: Board Diagnóstico #1 - A Mesa", "2026-03-10T13:20:00-03:00", "Wallace França"),
    ("69b2aac74ddb450012bb2096", "Tiago Mota: Board Diagnóstico #2 - A Mesa",     "2026-03-12T12:00:00-03:00", "Tiago Mota"),
    ("69b40a635278560013577dab", "Igor Della Croce: Board Diagnóstico #1 - A Mesa","2026-03-13T13:00:00-03:00","Igor Della Croce"),
    ("69b7fed7e108b900136af62d", "César Canal: Board Diagnóstico #1 - A Mesa",    "2026-03-16T13:00:00-03:00", "César Canal"),
    ("69b95797df37320013d2a758", "Rodrigo Rocha: Board Diagnóstico #1 - A Mesa",  "2026-03-17T13:31:00-03:00", "Rodrigo Rocha"),
    ("69bc2b9e06969c00138cd854", "Lucas Meireles: Board Diagnóstico #2 - A Mesa", "2026-03-19T17:00:00-03:00", "Lucas Meireles"),
    ("69bc3500771a48001353554e", "Lucas Meireles: Board Diagnóstico #2b - A Mesa","2026-03-19T17:40:00-03:00", "Lucas Meireles"),
    ("69bc4eaec1f67b0013e5d3b5", "João Victor: Onboarding - A Mesa",              "2026-03-19T19:30:00-03:00", "João Victor Pinheiro Silva"),
    ("69bc63c3c5ff720013461c45", "Giovanni Naddeo: Board Diagnóstico #1 - A Mesa","2026-03-19T21:00:00-03:00", "Giovanni Naddeo"),
    # --- Boards coletivos (cases apresentados ao grupo) ---
    ("69b1e5d4e108b900136a7861", "Encontro de boas-vindas — Board A Mesa Turma 1","2026-03-11T22:00:00-03:00", "Turma 1"),
    ("69c309bbfba84e001307733d", "Board Meeting #1 — Lucas Meireles · A Mesa",    "2026-03-24T22:01:00-03:00", "Lucas Meireles, Turma 1"),
    ("69d81d6312f6dd00136dcc5d", "Board Meeting #2 — Rodrigo Rocha · A Mesa",     "2026-04-09T21:42:00-03:00", "Rodrigo Rocha, Turma 1"),
    ("69debc278343c3001364d36a", "Board Meeting #2 extra — Rodrigo · A Mesa",     "2026-04-14T22:13:00-03:00", "Rodrigo Rocha"),
    ("69e92a46383a4f0013074d36", "Board Turma 1 — Eduardo Jones One:One",         "2026-04-22T20:06:00-03:00", "Eduardo Jones"),
    ("69fd0d1467d9840014a1fa95", "Board Meeting #3 — Hanna Castor · A Mesa",      "2026-05-07T22:07:00-03:00", "Hanna Castor, Turma 1"),
    # --- Sessões estratégicas / one:ones ---
    ("69d55508b1983400137df343", "Rodrigo Rocha: Reunião estratégica",             "2026-04-07T19:03:00-03:00", "Rodrigo Rocha"),
    ("69d65e8822f9190013a430db", "Giovanni Naddeo: One a One - A Mesa",            "2026-04-08T13:56:00-03:00", "Giovanni Naddeo"),
    ("69fb42610f3f8300130d512e", "Wallace França: Sessão de Decisão Estratégica",  "2026-05-06T13:30:00-03:00", "Wallace França"),
    # --- Outras reuniões Mesa relevantes ---
    ("69b3fc534ddb450012bb4ee7", "Alinhamento MESA/PESSOAS",                      "2026-03-13T12:00:00-03:00", "Felipe Gaudêncio, Alexandre"),
    ("69b95e75afb4b00013f5bf0e", "Semanal MESA",                                   "2026-03-17T14:00:00-03:00", "Caio Machado, Antonio Moreno"),
    ("69b98f91230f04001374e3d9", "A MESA - Juliana",                               "2026-03-17T17:30:00-03:00", "Juliana"),
    ("69bafd2e06969c00138cb2d5", "MESA + DNIA",                                    "2026-03-18T19:30:00-03:00", "Carlos Soares"),
    ("69d3f16f85eb2300138218d7", "Reunião - Adriana Marri",                        "2026-04-06T17:46:00-03:00", "Adriana Marri"),
    ("69f10b3c2ca21e0013c01024", "Reunião Lucas Gabriel",                           "2026-04-28T19:32:00-03:00", "Lucas Gabriel"),
    ("69e8d8a49a17d20013eb315b", "Lucas Gabriel - APP",                             "2026-04-22T14:18:00-03:00", "Lucas Gabriel"),
    ("69fbabcd06bece0013117669", "A Mesa — Conversa César + Rodrigo",              "2026-05-06T21:00:00-03:00", "César Canal, Rodrigo Rocha"),
    ("69fc93e0c1e4cf0013509b1c", "Maiara & Luiz",                                  "2026-05-07T13:30:00-03:00", "Maiara"),
    ("6a0f3308c90b3a0013417aab", "[CIS] Lígia Oliveira & Luiz Gustavo",            "2026-05-21T16:30:00-03:00", "Lígia Oliveira"),
    ("6a16f1ebbf173d001368c8f6", "[PROP] HACOO & MESA/BRENDI",                     "2026-05-27T13:30:00-03:00", "Hanna Castor, HACOO, Brendi"),
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
