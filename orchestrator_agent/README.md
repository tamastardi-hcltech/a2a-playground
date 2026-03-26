# Orchestrator Agent

A2A orchestrator that selectively calls downstream agents and merges only the relevant signals into one response.

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
- `TAROT_AGENT_URL` (default `http://127.0.0.1:8002`)

Example:

```bash
WEB_SEARCH_AGENT_URL=http://127.0.0.1:8000 \
ASTROLOGY_AGENT_URL=http://127.0.0.1:8001 \
TAROT_AGENT_URL=http://127.0.0.1:8002 \
uv run --env-file .env python -m orchestrator_agent.main
```

## Tool Choice

The orchestrator uses ADK remote A2A tools, and the oracle itself decides which downstream agents to consult based on the user request.

- `WEB_SEARCH_AGENT_URL`: consulted for current facts, news, release notes, or web-backed questions
- `ASTROLOGY_AGENT_URL`: consulted for horoscope, zodiac sign, birth date, or astrology-framed requests
- `TAROT_AGENT_URL`: consulted for tarot requests and reflective/oracle-style guidance

It may call zero, one, or multiple downstream agents depending on relevance. The final response names which agents were consulted and which were intentionally skipped.

Optional env vars:

- `ORCHESTRATOR_INPUT_GATE_MODEL` (default `gpt-4o-mini`)

## Task Lifecycle

- Emits `working` updates while selecting and consulting downstream agents
- Emits `input-required` only when astrology is selected and no sign/birth date is available yet
- Completes even if a selected downstream agent fails or times out, as long as at least one useful signal remains
