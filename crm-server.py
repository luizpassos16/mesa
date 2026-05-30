#!/usr/bin/env python3
"""Servidor local CRM Mesa — serve o HTML e faz proxy para o Supabase."""
import json, os, urllib.request, urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

SB_URL = os.environ.get("SB_URL", "").rstrip("/")
SB_KEY = os.environ.get("SB_KEY", "")
PORT    = int(os.environ.get("PORT", 8787))
ROOT    = os.path.dirname(os.path.abspath(__file__))

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  {self.address_string()} {fmt % args}")

    def do_GET(self):
        if self.path.startswith("/api/"):
            self._proxy()
        elif self.path in ("/", "/crm-local.html"):
            self._serve_file("crm-local.html", "text/html; charset=utf-8")
        else:
            self.send_error(404)

    def _serve_file(self, name, ctype):
        path = os.path.join(ROOT, name)
        try:
            with open(path, "rb") as f:
                data = f.read()
        except FileNotFoundError:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _proxy(self):
        # /api/people?full_name=ilike.*hanna*  →  SB_URL/rest/v1/people?...
        rest_path = self.path[len("/api"):]   # mantém /people?...
        url = f"{SB_URL}/rest/v1{rest_path}"
        req = urllib.request.Request(url, headers={
            "apikey":        SB_KEY,
            "Authorization": "Bearer " + SB_KEY,
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
                status = r.status
        except urllib.error.HTTPError as e:
            body = e.read()
            status = e.code

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    if not SB_URL or not SB_KEY:
        raise SystemExit("Defina SB_URL e SB_KEY antes de rodar.")
    print(f"Mesa CRM rodando em http://127.0.0.1:{PORT}/")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
