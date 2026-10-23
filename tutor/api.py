"""Minimal JSON API (standard library only).

  python -m tutor.api            # serves http://127.0.0.1:8000
  GET /health
  GET /ask?q=fifth+grade+rounding+decimals
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .answer import ask

MAX_Q = 300


def respond(question: str) -> dict:
    r = ask(question[:MAX_Q])
    return {
        "question": question[:MAX_Q],
        "answered": r.answered,
        "answer": r.answer,
        "citations": r.citations,
        "matches": [{"teks_code": h.teks_code, "subject": h.subject_name, "citation": h.citation, "grade": h.grade,
                     "strand": h.strand, "text": h.text, "score": round(h.score, 2)} for h in r.hits[:3]]
        if r.answered else [],
        "understood": {"grade": r.info.get("grade_filter"), "subject": r.info.get("subject_filter"),
                       "code": r.info.get("code"), "corrected": r.info.get("corrected", [])},
        "source": "Texas Essential Knowledge and Skills, K-5, revised June 2024 (TEA; published for information only)",
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        u = urlparse(self.path)
        if u.path == "/health":
            return self._send(200, {"ok": True})
        if u.path == "/ask":
            q = (parse_qs(u.query).get("q") or [""])[0].strip()
            if not q:
                return self._send(400, {"error": "missing q"})
            return self._send(200, respond(q))
        self._send(404, {"error": "not found"})

    def log_message(self, *a) -> None:  # keep logs free of user questions
        pass


def serve(port: int = 8000) -> None:
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    serve()
