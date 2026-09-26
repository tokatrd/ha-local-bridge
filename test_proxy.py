"""Smoke test: keyword fallback works with no Ollama running."""

from ollama_proxy import keyword_parse

assert keyword_parse("turn on kitchen light")["service"] == "light.turn_on"
assert keyword_parse("turn off tv")["service"] == "light.turn_off"
assert keyword_parse("hello")["service"] == "conversation.reply"
print("ha-local-bridge smoke OK")
