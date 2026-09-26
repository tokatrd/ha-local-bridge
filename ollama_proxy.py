"""Ollama -> HA intent bridge. Stdlib only. Works offline via keyword fallback."""

import argparse, json, re, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

INTENTS = [
    (re.compile(r"turn on (.+)"), "light.turn_on"),
    (re.compile(r"switch on (.+)"), "switch.turn_on"),
    (re.compile(r"turn off (.+)"), "light.turn_off"),
    (re.compile(r"switch off (.+)"), "switch.turn_off"),
    (re.compile(r"open (.+)"), "cover.open_cover"),
    (re.compile(r"close (.+)"), "cover.close_cover"),
]


def keyword_parse(text):
    t = text.strip().lower()
    for pat, service in INTENTS:
        m = pat.search(t)
        if m:
            return {"service": service, "entity": m.group(1).strip().replace(" ", "_")}
    return {
        "service": "conversation.reply",
        "entity": None,
        "reply": "No intent matched; forwarded to LLM.",
    }


def ollama_chat(ollama_base, model, prompt, timeout=20):
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
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode()).get("message", {}).get("content", "")
    except Exception as e:
        return f"__OLLAMA_DOWN__: {e}"


SYSTEM = 'You control Home Assistant. Reply with ONLY JSON: {"service": "domain.service", "entity": "friendly_name_snake"}.'


class H(BaseHTTPRequestHandler):
    ollama = "http://localhost:11434"
    model = "llama3.1:8b"

    def _send(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            payload = {}
        msgs = payload.get("messages", [])
        user_text = next(
            (m.get("content", "") for m in reversed(msgs) if m.get("role") == "user"),
            "",
        )
        local = keyword_parse(user_text)
        if local["service"] != "conversation.reply":
            return self._send(
                {
                    "id": "local",
                    "object": "chat.completion",
                    "choices": [
                        {"message": {"role": "assistant", "content": json.dumps(local)}}
                    ],
                }
            )
        llm = ollama_chat(self.ollama, self.model, SYSTEM + "\nUser: " + user_text)
        return self._send(
            {
                "id": "ollama",
                "object": "chat.completion",
                "choices": [{"message": {"role": "assistant", "content": llm}}],
            }
        )

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ollama", default="http://localhost:11434")
    ap.add_argument("--model", default="llama3.1:8b")
    ap.add_argument("--port", type=int, default=8099)
    a = ap.parse_args()
    H.ollama = a.ollama
    H.model = a.model
    print(f"ha-local-bridge on :{a.port} -> {a.ollama} ({a.model})")
    HTTPServer(("127.0.0.1", a.port), H).serve_forever()
