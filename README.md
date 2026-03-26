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
- `ui_app/streamlit_app.py`: minimal chat frontend for interacting with the orchestrator
  - supports A2A `input-required` follow-up for missing astrology birth date

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

6. Run chat UI (optional)

```bash
uv run --env-file .env streamlit run ui_app/streamlit_app.py
```

## One-command startup

Start all four backend services in one terminal:

```bash
./scripts/start_all.sh
```

This starts `web_search_agent`, `astrology_agent`, `tarot_agent`, and `orchestrator_agent`.
Logs are written under `logs/`.

## Docker Compose

Run everything (all agents + Streamlit UI):

```bash
docker compose up --build
```

Each service is built from its own Dockerfile (`<service>/Dockerfile`) to simulate separate deployments.

Endpoints:

- Web search agent: `http://127.0.0.1:8000`
- Astrology agent: `http://127.0.0.1:8001`
- Tarot agent: `http://127.0.0.1:8002`
- Orchestrator: `http://127.0.0.1:8010`
- UI: `http://127.0.0.1:8501`

Stop and remove containers:

```bash
docker compose down
```

## Env vars

Common:

- `OPENAI_API_KEY`
- `LOG_LEVEL` (default `INFO`)

Orchestrator:

- `ORCHESTRATOR_MODEL` (default `openai/gpt-5`)
- `ORCHESTRATOR_INPUT_GATE_MODEL` (default `gpt-4o-mini`)
- `ASTROLOGY_AGENT_URL` (default `http://127.0.0.1:8001`)
- `WEB_SEARCH_AGENT_URL` (default `http://127.0.0.1:8000`)
- `TAROT_AGENT_URL` (default `http://127.0.0.1:8002`)

Web search:

- `SEARCH_MODEL` (default `gpt-5`)
- `DDG_BACKEND` (default `duckduckgo`)

## How The Demo Routes Work

The orchestrator now uses the ADK remote-agent setup again, so the oracle itself chooses which downstream tools to call for a request instead of consulting every service by default.

- `web_search_agent`: used for current events, external facts, release notes, or clearly web-backed questions
- `astrology_agent`: used for sign, birth date, horoscope, or astrology-framed guidance
- `tarot_agent`: used for reflective/oracle-style prompts, tarot requests, and open-ended guidance

Examples:

- "Find the latest TypeScript release notes" -> web search only
- "Daily horoscope for 1993-08-12" -> astrology only
- "Draw 3 cards for my project" -> tarot only
- "How is my week looking? I am leo." -> astrology + tarot

The final orchestrator answer includes:

- which agents it consulted
- which agents it intentionally skipped
- any unavailable downstream signals
- the final synthesized oracle answer

## A2A Task Behavior

This repo is meant to show the A2A task lifecycle across separate services.

- The orchestrator emits `working` updates while it selects agents and calls each downstream service.
- The tarot agent emits multiple `working` updates, one per card reveal, before its final `completed` message.
- The orchestrator can emit `input-required` when astrology is selected and it needs a birth date that was not already provided.
- The Streamlit UI shows the collected task progress in an "A2A task progress" section for each reply.

## Notes

- This is a starter skeleton intended to be extended.
- Outputs are plain text and intentionally human-readable for demo purposes.
