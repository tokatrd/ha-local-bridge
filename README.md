# ha-local-bridge

I run Home Assistant and wanted to use a local Ollama model instead of sending everything to a cloud API, so I put together this small bridge. No hosted inference — you run Ollama, this shim translates.

**What it does:**
- Exposes an OpenAI-compatible `/v1/chat/completions` endpoint that forwards to Ollama (`http://localhost:11434`).
- Forces properly formatted HA service calls via constrained prompt + regex fallback.
- If Ollama is down, falls back to a keyword intent parser so basics still work.

## Run
```bash
python3 ollama_proxy.py --ollama http://localhost:11434 --port 8099
python3 test_proxy.py
```
Point your HA LLM conversation integration at `http://localhost:8099/v1`.

*Put together with some AI help.*
