# a2a_agents

Minimal multi-agent A2A starter project.

## What is included

- `web_search_agent`: A2A agent with LangChain + DuckDuckGo tool.
- `astrology_agent`: A2A agent with synthetic astrology tools.
- `tarot_agent`: A2A streaming tarot agent with delayed card-by-card reveals.
- `orchestrator_agent`: Google ADK agent that orchestrates remote A2A sub-agents.
- `main.py`: root entrypoint
  - `serve` mode: runs orchestrator server
  - `ask` mode: sends one question to orchestrator as a client

## Quick start

Run each service in a separate terminal.

1. Web search agent (port `8000`)

```bash
uv run --env-file web_search_agent/.env python -m web_search_agent.main
```

2. Astrology agent (port `8001`)

```bash
uv run --env-file astrology_agent/.env python -m astrology_agent.main
```

3. Tarot agent (port `8002`)

```bash
uv run --env-file tarot_agent/.env python -m tarot_agent.main
```

4. Orchestrator (port `8010`)

```bash
uv run --env-file orchestrator_agent/.env python -m orchestrator_agent.main
```

5. Ask orchestrator from root

```bash
uv run --env-file .env python main.py ask "How will my day look if I am a cancer?"
```

## Env vars

Common:

- `OPENAI_API_KEY`
- `LOG_LEVEL` (default `INFO`)

Orchestrator:

- `ORCHESTRATOR_MODEL` (default `openai/gpt-5`)
- `ASTROLOGY_AGENT_URL` (default `http://127.0.0.1:8001`)
- `WEB_SEARCH_AGENT_URL` (default `http://127.0.0.1:8000`)
- `TAROT_AGENT_URL` (default `http://127.0.0.1:8002`)

Web search:

- `SEARCH_MODEL` (default `gpt-5`)
- `DDG_BACKEND` (default `duckduckgo`)

## Notes

- This is a starter skeleton intended to be extended.
- Outputs are plain text, no structured response schema.
