"""Smoke: keyword fast path, safe fallback, envelope shape. No Ollama needed."""

import json, threading, urllib.error, urllib.request
from http.server import HTTPServer
import ollama_proxy as P

srv = HTTPServer(("127.0.0.1", 18099), P.H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
try:

    def post(text, path="/v1/chat/completions"):
        body = json.dumps({"messages": [{"role": "user", "content": text}]}).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:18099{path}",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, None

    s, r = post("turn on kitchen light")
    assert s == 200, s
    assert r is not None
    assert (
        json.loads(r["choices"][0]["message"]["content"])["service"] == "light.turn_on"
    )
    assert r["choices"][0]["finish_reason"] == "stop" and "model" in r and "usage" in r

    # wrong path must 404, not 200 (masks misconfiguration otherwise)
    s, _ = post("turn on x", path="/nope")
    assert s == 404, s

    # no Ollama running here -> safe text fallback, never a traceback
    P.H.ollama = "http://127.0.0.1:9"
    s, r = post("tell me a story")
    assert s == 200, s
    assert r is not None
    content = r["choices"][0]["message"]["content"]
    assert "__OLLAMA_DOWN__" not in content and "Traceback" not in content, content

    # helpers
    assert P.extract_json('here {"service": "light.turn_on"} ok') == {
        "service": "light.turn_on"
    }
    assert P.extract_json("no json here") is None
    assert P.keyword_parse("dim the lights") is None
finally:
    srv.shutdown()
print("ha-local-bridge smoke OK")
