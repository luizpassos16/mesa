#!/usr/bin/env python3
"""Sync Gmail → CRM da Mesa.

Extrai contatos reais de threads do Gmail (excluindo newsletters/notificações)
e cria person_insights (kind=meeting, source=gmail:{thread_id}).

Uso:
    # 1. Exporta threads via MCP Gmail e salva em /tmp/gmail_threads.json
    #    (formato: list de {id, subject, date, senders, recipients})
    # 2. Roda o script:
    export SB_URL="..." SB_KEY="..."
    python3 scripts/sync_gmail.py [--arquivo /tmp/gmail_threads.json]

Lógica de filtro:
- Remove self (lgcmp44@gmail.com)
- Remove domínios de newsletters/marketing
- Remove noreply/mailer-daemon
- Mantém só e-mails humanos com domínio empresarial ou pessoal real
"""
import json, os, sys, re, urllib.request, urllib.parse

SB_KEY = os.environ["SB_KEY"]
SB_URL = os.environ["SB_URL"].rstrip("/")
LUIZ   = "lgcmp44@gmail.com"

# Padrões de ruído — newsletters, marketing, sistemas
NOISE = [
    r'noreply|no-reply|mailer-daemon',
    r'^(mkt|marketing|newsletter|relacionamento|comunicacao|atendimento|notifications|notify|invoice|automacao|assinatura)@',
    r'@(mkt\.|mail\.|mailing\.|email\.|marketing\.|relacionamento\.|newsletter\.)',
    r'@(substack\.com|beehiiv\.com|beehiiv\.io|growthhackers\.com)',
    r'@(mail\.c6bank|mkt\.magalu|mkt\.tf|mail\.infinitepay|email\.viacaocometa)',
    r'@(research\.xpi|info\.infomoney|mail\.beehiiv|mails\.latam|mail\.infolivelo)',
    r'@(thenewscc|picpay\.com|azos\.com|zapier\.com|academia-mail|wispr\.ai)',
    r'@(sympla\.com|formulahighticket|higgsfield\.ai|littlebean|oficina\.com)',
    r'@(g4educacao\.com|investimentos\.one)',  # marketing lists dessas empresas (ok para convites reais)
    r'executive.?assistant@',
    r'@e\.read\.ai',
    r'@stripe\.com|@paypal|@ifood',
]
NOISE_RE = [re.compile(p, re.IGNORECASE) for p in NOISE]

# Exceções — domínios que PODEM ser ruído mas são parceiros reais
WHITELIST = ['evellyn.mendes@g4educacao.com', 'thiago.oliveira@investimentos.one',
             'gabriel.castelo@investimentos.one', 'joao.neto@investimentos.one']


def is_noise(email):
    if email.lower() == LUIZ:
        return True
    if email.lower() in WHITELIST:
        return False
    for rx in NOISE_RE:
        if rx.search(email):
            return True
    return False


def sb(path, params=None, body=None, method="GET"):
    qs = ("?" + urllib.parse.urlencode(params or {})) if params else ""
    req = urllib.request.Request(
        f"{SB_URL}/rest/v1/{path}{qs}",
        data=json.dumps(body).encode() if body else None,
        method=method,
        headers={
            "apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY,
            "Content-Type": "application/json",
            "Prefer": "resolution=ignore-duplicates,return=minimal",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        return json.loads(raw) if raw else []


def find_person(email):
    rows = sb("person_identities", {
        "kind": "eq.email",
        "value_norm": f"eq.{email.lower()}",
        "select": "person_id",
        "limit": "1",
    })
    return rows[0]["person_id"] if rows else None


def main():
    arquivo = "/tmp/gmail_threads.json"
    for i, arg in enumerate(sys.argv):
        if arg == "--arquivo" and i + 1 < len(sys.argv):
            arquivo = sys.argv[i + 1]

    with open(arquivo) as f:
        threads = json.load(f)

    print(f"# {len(threads)} threads para processar\n")

    seen = set()
    insights = []

    for t in threads:
        tid     = t.get("id", "")
        subject = t.get("subject", "(sem assunto)")
        date    = t.get("date", "")[:10]

        # Coleta todos os emails do thread
        all_emails = set()
        for msg in t.get("messages", []):
            for field in ["sender", "toRecipients", "ccRecipients"]:
                v = msg.get(field, "")
                if isinstance(v, str):
                    all_emails.add(v)
                elif isinstance(v, list):
                    all_emails.update(v)

        for email in all_emails:
            email = email.lower().strip()
            if not email or is_noise(email):
                continue
            pid = find_person(email)
            if not pid:
                continue
            key = (pid, f"gmail:{tid}")
            if key in seen:
                continue
            seen.add(key)
            insights.append({
                "person_id":    pid,
                "kind":         "meeting",
                "source":       f"gmail:{tid}",
                "text_content": f'Thread "{subject}" ({date}). Contato via Gmail.',
            })

    print(f"Insights a inserir: {len(insights)}")

    # Insere em lotes
    hdrs = {
        "apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY,
        "Content-Type": "application/json",
        "Prefer": "resolution=ignore-duplicates,return=minimal",
    }
    ok = 0
    for i in range(0, len(insights), 50):
        batch = insights[i:i+50]
        req = urllib.request.Request(
            f"{SB_URL}/rest/v1/person_insights",
            data=json.dumps(batch).encode(), method="POST", headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                r.read()
            ok += len(batch)
        except Exception as e:
            print(f"  erro: {e}")

    print(f"# {ok} insights criados")


if __name__ == "__main__":
    main()
