# ha-local-bridge

I run Home Assistant and wanted to use a local Ollama model instead of sending everything to a cloud API, so I put together this small bridge. It returns service calls as chat JSON — something (see `ha_example.yaml`) has to actually call them.

## Prerequisites

- Python 3.10+ (stdlib only, no pip install needed).
- Ollama installed, serving, with a model pulled: `ollama serve` then `ollama pull llama3.1:8b` (~5 GB).

## Run

Terminal 1 — the proxy (blocks):

```bash
python3 ollama_proxy.py --ollama http://localhost:11434 --model llama3.1:8b --port 8099
```

Terminal 2 — the test:

```bash
python3 test_proxy.py  # expect: ha-local-bridge smoke OK
```

## Point Home Assistant at it

Use the **OpenAI Conversation** integration (or the HACS Extended OpenAI Conversation): base URL `http://<this-machine>:8099/v1`, any dummy API key, model `llama3.1:8b`, streaming off. Same-machine only unless you bind `--host 0.0.0.0` (and point Ollama at your LAN IP with `OLLAMA_HOST`).

`ha_example.yaml` shows one way to turn the returned JSON into a real service call — adapt the entity mapping to your house.

## Limitations

- 6 phrasings are answered locally (turn/switch on-off, open/close); everything else goes to the model.
- The `entity` guess is `spaces → underscores`, not a real `entity_id` — you need the mapping step.
- No brightness/climate/locks/scenes/queries; no streaming; no `/v1/models` discovery.
- Small local models wrap JSON in prose; the proxy extracts the first `{...}` block and passes the rest through raw.

MIT — see LICENSE.

*Put together with some AI help.*
