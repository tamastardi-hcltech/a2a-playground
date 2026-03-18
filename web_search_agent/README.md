# Web Search Agent

Simple A2A agent that answers queries with web-search-backed context.

## Run

```bash
uv run --env-file web_search_agent/.env python -m web_search_agent.main
```

Default port is `8000`. Override with:

```bash
A2A_PORT=8000 uv run --env-file web_search_agent/.env python -m web_search_agent.main
```

## Notes

- Uses `OPENAI_API_KEY` from env.
- Exposes A2A endpoints (agent card + JSON-RPC) on the configured port.
