"""Ollama -> Home Assistant intent bridge. Stdlib only.

Fast path: 6 common phrasings are answered locally without calling the model.
Everything else is forwarded to Ollama and returned in an OpenAI-compatible
envelope. If Ollama is down you get a plain-text fallback, never a traceback.
"""

import argparse, json, re, time, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

INTENTS = [
    (re.compile(r"turn on (.+)"), "light.turn_on"),
    (re.compile(r"switch on (.+)"), "switch.turn_on"),
    (re.compile(r"turn off (.+)"), "light.turn_off"),
    (re.compile(r"switch off (.+)"), "switch.turn_off"),
    (re.compile(r"open (.+)"), "cover.open_cover"),
    (re.compile(r"close (.+)"), "cover.close_cover"),
]

FALLBACK = "Local model unavailable — try a simple command like 'turn on …'."


def keyword_parse(text):
    t = text.strip().lower()
    for pat, service in INTENTS:
        m = pat.search(t)
        if m:
            return {"service": service, "entity": m.group(1).strip().replace(" ", "_")}
    return None


def extract_json(text):
    """Pull the first {...} block out of model prose; None if there isn't one."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def ollama_chat(ollama_base, model, prompt, timeout=60):
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
    ).encode()
    req = urllib.request.Request(
        ollama_base.rstrip("/") + "/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode()).get("message", {}).get("content", "")


SYSTEM = (
    "You control Home Assistant. Reply with ONLY this JSON, no other text: "
    '{"service": "domain.service", "entity": "area_or_device_name"}'
)


class H(BaseHTTPRequestHandler):
    ollama = "http://localhost:11434"
    model = "llama3.1:8b"

    def _send(self, content, cid, code=200):
        obj = {
            "id": cid,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": self.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path.split("?")[0] != "/v1/chat/completions":
            self.send_response(404)
            self.end_headers()
            return
        n = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            payload = {}
        msgs = payload.get("messages", [])
        user_text = next(
            (m.get("content", "") for m in reversed(msgs) if m.get("role") == "user"),
            "",
        )

        local = keyword_parse(user_text)
        if local is not None:
            return self._send(json.dumps(local), "local")

        try:
            llm = ollama_chat(self.ollama, self.model, SYSTEM + "\nUser: " + user_text)
        except Exception:
            return self._send(FALLBACK, "fallback")

        parsed = extract_json(llm)
        return self._send(json.dumps(parsed) if parsed is not None else llm, "ollama")

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--ollama",
        default="http://localhost:11434",
        help="Ollama base URL (use http://<lan-ip>:11434 if HA/proxy are on different machines)",
    )
    ap.add_argument(
        "--model",
        default="llama3.1:8b",
        help="model must already be pulled: ollama pull <model>",
    )
    ap.add_argument(
        "--host", default="127.0.0.1", help="bind address; 0.0.0.0 to reach it over LAN"
    )
    ap.add_argument("--port", type=int, default=8099)
    a = ap.parse_args()
    H.ollama, H.model = a.ollama, a.model
    print(f"ha-local-bridge on {a.host}:{a.port} -> {a.ollama} ({a.model})")
    HTTPServer((a.host, a.port), H).serve_forever()
