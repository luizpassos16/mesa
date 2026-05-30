#!/usr/bin/env python3
"""Carrega transcrições Granola (.txt) para a tabela granola_transcripts via REST Supabase.

Uso:
    export SB_URL="https://hgwjvfgntfpvgdghngtn.supabase.co"
    export SB_KEY="<service_role key>"
    python3 scripts/load_granola_transcripts.py

Lê todos os .txt em transcricoes-granola/, faz upsert idempotente.
"""
import json, os, glob, urllib.request, sys

SB_KEY = os.environ["SB_KEY"]
SB_URL = os.environ["SB_URL"].rstrip("/")
ENDPOINT = SB_URL + "/rest/v1/granola_transcripts"

TRANSCRIPT_DIR = os.path.join(os.path.dirname(__file__), "..", "transcricoes-granola")

# meeting_id → (title, meeting_date ISO)
METADATA = {
    "16bc938d-01f1-463f-8f6f-82ab11a766b1": ("MESA + Brendi", "2026-05-22T18:00:00-03:00"),
    "17737a92-028d-4190-b871-57e45494681d": ("Comunidade e modelo de negócio — Alfredo/Giovanni", "2026-05-28T17:59:00-03:00"),
    "1e8ec761-6460-4819-9a0e-9f91a6cceef4": ("Conexão Victor Gontijo + Daniel Frageri", "2026-05-15T15:30:00-03:00"),
    "3195ed01-6975-4319-a839-d24a10f95b01": ("Reunião — Luiz & Wellington", "2026-05-14T11:00:00-03:00"),
    "38866bd7-56f1-44ac-86e3-6b65226f87c8": ("Sessão de Decisão Estratégica — Wallace França", "2026-05-06T10:30:00-03:00"),
    "61f2e5bc-8c30-48ad-8aef-43a37bb81ce6": ("Conversa com Vitinho — Imposto e Taxa", "2026-05-09T11:00:00-03:00"),
    "66aef302-8793-4dc2-8513-48898243b496": ("Preparação Board #3 — Hanna Castor", "2026-04-30T17:00:00-03:00"),
    "6ebc8d1b-4889-4433-b863-c36a1a6854b7": ("Encontro MCA+", "2026-04-30T14:00:00-03:00"),
    "7b8b801e-f015-487a-a02b-7b0424287e49": ("[CIS] Lígia Oliveira & Luiz Gustavo", "2026-05-21T13:30:00-03:00"),
    "7d46785d-734c-4c66-bfc7-f87f7f303bd9": ("A Mesa — Conversa sobre o evento (César + Rodrigo)", "2026-05-06T18:00:00-03:00"),
    "d3ea17bd-13cc-48f8-9f43-6b075fcd33e6": ("Hot Seat Bônus — Turma 1", "2026-04-28T19:00:00-03:00"),
    "eb1298fb-d387-4872-b40b-0c9ba1a48bd9": ("Maiara & Luiz (Fortini)", "2026-05-07T10:30:00-03:00"),
    "f90c3526-c30c-4745-b74e-1eb237e9d3f6": ("Precificação mentoria — César e Rodrigo", "2026-05-14T20:01:00-03:00"),
    "38cfc468-b34b-4c81-99e3-1f41ba7f67c9": ("[PROP] HACOO & MESA/BRENDI", "2026-05-27T10:30:00-03:00"),
    "cad57093-0a90-492c-bb79-5f925c968631": ("Reunião Igor A Mesa", "2026-05-26T17:00:00-03:00"),
    "f048d96d-24a2-449a-b03d-d72c3110a1c1": ("Parceria | One + Mesa v2", "2026-05-18T16:00:00-03:00"),
    "0df3fc4c-94e1-48b3-8ff9-a0ce722d365d": ("Parceria | Mesa + One v1", "2026-05-06T14:30:00-03:00"),
    "b2ec763a-ac9f-4516-b2f1-34b282034eaf": ("MESA + CRIE — Trocas entre as Empresas", "2026-05-05T11:00:00-03:00"),
    "4f0c950b-2b49-42e8-a9fb-6f2397da08a3": ("Reunião Luiz Passos | Build in Public", "2026-05-04T10:00:00-03:00"),
    "0b1e034b-f0d9-45ef-9b8c-f115e450b3e4": ("A Mesa + MVP", "2026-04-28T15:00:00-03:00"),
    "0cad7ca2-b849-4d34-9bc2-123717d04b56": ("Estratégia de produtos e conteúdo com Tamara", "2026-05-27T14:03:00-03:00"),
    "507c9bce-0df3-4ac8-88d3-6fae96a6a2cb": ("Metodologia 360 com Hana", "2026-05-22T10:38:00-03:00"),
}

def upsert(meeting_id, title, date, transcript):
    body = json.dumps([{
        "meeting_id": meeting_id,
        "title": title,
        "meeting_date": date,
        "transcript": transcript,
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
    ok = stored == len(transcript)
    status = "OK  " if ok else "WARN"
    print(f"{status}  {meeting_id[:8]}  enviado={len(transcript):,}  gravado={stored:,}  {title[:45]}")
    return ok

def main():
    paths = sorted(glob.glob(os.path.join(TRANSCRIPT_DIR, "*.txt")))
    if not paths:
        print(f"Nenhum .txt encontrado em {TRANSCRIPT_DIR}")
        sys.exit(1)
    print(f"# {len(paths)} arquivo(s) encontrado(s)")
    ok_count = 0
    for path in paths:
        meeting_id = os.path.basename(path).replace(".txt", "")
        meta = METADATA.get(meeting_id)
        if not meta:
            print(f"SKIP  {meeting_id[:8]}  (sem metadados)")
            continue
        title, date = meta
        with open(path, encoding="utf-8") as f:
            transcript = f.read().strip()
        if not transcript:
            print(f"SKIP  {meeting_id[:8]}  (arquivo vazio)")
            continue
        try:
            if upsert(meeting_id, title, date, transcript):
                ok_count += 1
        except Exception as e:
            print(f"ERRO  {meeting_id[:8]}  {str(e)[:120]}")
    print(f"\n# {ok_count}/{len(paths)} carregadas com char_count batendo")

if __name__ == "__main__":
    main()
