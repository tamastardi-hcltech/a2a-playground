# Orchestrator Agent

A2A orchestrator that calls other agents and merges their outputs into one response.

## Run

```bash
uv run --env-file .env python -m orchestrator_agent.main
```

Default port is `8010`. Override with:

```bash
A2A_PORT=8010 uv run --env-file .env python -m orchestrator_agent.main
```

## Expected Downstream Agents

- `WEB_SEARCH_AGENT_URL` (default `http://127.0.0.1:8000`)
- `ASTROLOGY_AGENT_URL` (default `http://127.0.0.1:8001`)

Example:

```bash
WEB_SEARCH_AGENT_URL=http://127.0.0.1:8000 \
ASTROLOGY_AGENT_URL=http://127.0.0.1:8001 \
uv run --env-file .env python -m orchestrator_agent.main
```
