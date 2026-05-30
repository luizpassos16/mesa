#!/usr/bin/env python3
"""Gera/atualiza embeddings de pessoas via OpenAI text-embedding-3-small.

Modos:
  python3 scripts/generate_embeddings.py              # só pessoas sem embedding
  python3 scripts/generate_embeddings.py --all        # regenera todos
  python3 scripts/generate_embeddings.py --turma1     # só membros da Turma 1

Requer: OPENAI_API_KEY, SB_URL, SB_KEY no ambiente.
"""
import json, os, sys, urllib.request, urllib.parse, time

SB_KEY       = os.environ["SB_KEY"]
SB_URL       = os.environ["SB_URL"].rstrip("/")
OPENAI_KEY   = os.environ["OPENAI_API_KEY"]
EMBED_MODEL  = "text-embedding-3-small"

# IDs dos membros da Turma 1
TURMA1_IDS = {
    "4cfa4744-28fa-4f63-8415-4020bb79adec",  # César
    "60fc5947-b37c-4743-903d-e40b694cd7dc",  # Giovanni
    "4f3e3878-45f7-4537-8ce7-c37420c056f3",  # Hanna
    "753fe8a3-c626-437c-8ca9-1d15fb46be42",  # Henrique
    "568e588d-aa0b-48f5-87ff-0f0cfe25a98e",  # Igor
    "cae0fc9b-1ce6-4b4e-9e2a-b48d20f41355",  # João Victor
    "cbdae66c-75df-4a84-86a1-731945dcf93d",  # Lucas
    "0fcf2095-b688-4a55-ad68-2874d8e6ca9f",  # Rodrigo
    "627d3d9f-b056-4e7e-bd45-f575b80c123f",  # Tiago
    "611c407b-490a-4dba-b3b8-0265704d1e67",  # Wallace
    "a60bb9d0-a012-416b-b552-b36ace0f1cf2",  # Wellington
}


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


def embed(text):
    body = json.dumps({"input": text, "model": EMBED_MODEL}).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/embeddings",
        data=body, method="POST",
        headers={
            "Authorization": f"Bearer {OPENAI_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read())
        return d["data"][0]["embedding"]


def build_content(person, insights):
    parts = [f"Nome: {person['full_name']}"]
    if person.get("company_name"):  parts.append(f"Empresa: {person['company_name']}")
    if person.get("segment"):       parts.append(f"Segmento: {person['segment']}")
    if person.get("role"):          parts.append(f"Cargo: {person['role']}")
    if person.get("city"):          parts.append(f"Cidade: {person['city']}")
    if person.get("primary_email"): parts.append(f"Email: {person['primary_email']}")

    kind_map = {"about": "Sobre", "goal": "Objetivo", "pain": "Dor",
                "challenge": "Desafio", "trajectory": "Trajetória",
                "motivation": "Motivação", "wish": "Desejo",
                "intro_phrase": "Apresentação", "lifestyle": "Estilo de vida"}
    for k, label in kind_map.items():
        texts = [i["text_content"] for i in insights if i["kind"] == k]
        if texts:
            parts.append(f"{label}: {' | '.join(t[:200] for t in texts[:2])}")

    return "\n".join(parts)


def process_person(person):
    pid = person["id"]
    insights = sb("person_insights", {
        "person_id": f"eq.{pid}",
        "select": "kind,text_content",
        "kind": "neq.meeting",
    })
    content = build_content(person, insights)
    if len(content) < 20:
        return False  # sem dados suficientes

    vector = embed(content)
    sb("person_embeddings", body=[{
        "person_id": pid,
        "content": content,
        "embedding": vector,
        "model": EMBED_MODEL,
    }], method="POST")
    return True


def main():
    mode_all    = "--all"    in sys.argv
    mode_turma1 = "--turma1" in sys.argv

    # Remove registro de teste
    sb("people", {"full_name": "eq.__LIXO_TESTE__"}, method="DELETE")

    if mode_all:
        people = sb("people", {"select": "id,full_name,company_name,segment,role,city,primary_email", "limit": "600"})
    elif mode_turma1:
        people = [sb("people", {"id": f"eq.{pid}", "select": "id,full_name,company_name,segment,role,city,primary_email"})[0]
                  for pid in TURMA1_IDS]
    else:
        # Sem embedding + Cassiano + Carlos
        sem = sb("people", {
            "select": "id,full_name,company_name,segment,role,city,primary_email",
        })
        tem = {r["person_id"] for r in sb("person_embeddings", {"select": "person_id", "limit": "600"})}
        people = [p for p in sem if p["id"] not in tem]

    if mode_turma1:
        # Também inclui Cassiano e Carlos (sem embedding)
        extras = ["236990f0-2b12-4a18-9592-b4e75db661ff", "b40d33cd-0602-4f98-be14-6aee4e47eed6"]
        for pid in extras:
            rows = sb("people", {"id": f"eq.{pid}", "select": "id,full_name,company_name,segment,role,city,primary_email"})
            if rows:
                people.append(rows[0])

    print(f"# {len(people)} pessoa(s) para processar\n")
    ok = 0
    for p in people:
        try:
            if process_person(p):
                ok += 1
                print(f"  ✓ {p['full_name']}")
            else:
                print(f"  — {p['full_name']} (sem dados)")
            time.sleep(0.1)  # evita rate limit
        except Exception as e:
            print(f"  ✗ {p['full_name']}: {str(e)[:80]}")

    print(f"\n# {ok} embeddings gerados/atualizados")


if __name__ == "__main__":
    main()
