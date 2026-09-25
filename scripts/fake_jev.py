"""Local stand-in for the JEV System One API, for end-to-end runs where the real API is not
reachable. It validates the request shape the router sends and answers with the real response
schema (see tests/fixtures/jev_live_response.json), choosing a model by a keyword heuristic:
prompts containing "RENAME" pick the cheapest offered model, "ARCHITECT" the strongest,
anything else the middle one. It is NOT a substitute for the live test against the real API.

    python scripts/fake_jev.py 8765
    JEV_ENDPOINT=http://127.0.0.1:8765/v1/systemone TYPESAFE_API_KEY=local jev-claude ...
"""
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REQUIRED_QUESTIONS = {"task_complexity", "reasoning_required", "tool_complexity", "model"}


def _score(value: float) -> dict:
    return {"type": "score", "score": value, "confidence": 0.9}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        problems = []
        if not (self.headers.get("Authorization") or "").startswith("Bearer "):
            problems.append("missing bearer token")
        if set(body.get("questions", {})) != REQUIRED_QUESTIONS:
            problems.append(f"questions={sorted(body.get('questions', {}))}")
        offered = body.get("state", {}).get("environment", {}).get("available_models") or []
        if not offered or set(body["questions"]["model"]["criteria"]) != set(offered):
            problems.append("model criteria do not match available_models")
        if problems:
            self._send(400, {"error": "; ".join(problems)})
            return

        prompt = body["state"]["request"]
        pick = offered[0] if "RENAME" in prompt else offered[-1] if "ARCHITECT" in prompt else offered[len(offered) // 2]
        print(f"[fake-jev] request ok: {len(offered)} models offered -> {pick}", flush=True)
        self._send(200, {
            "model": "jev-fake",
            "answers": {
                "task_complexity": _score(1.0),
                "reasoning_required": _score(1.5),
                "tool_complexity": _score(1.0),
                "model": {"type": "choice", "choice": pick, "confidence": 0.97, "probabilities": {pick: 0.97}},
            },
        })

    def _send(self, status, payload):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"[fake-jev] listening on 127.0.0.1:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
