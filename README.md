# a2a_agents

Minimal multi-agent A2A starter project.

## Goals

This project was built as a hands-on experiment, not just as an app.

- Try Codex in a realistic coding workflow and see how far it could take a repo after the initial scaffolding.
- Explore how A2A works across separate services, separate agent cards, and an orchestrator that chooses which remote
  agents to consult.
- Compare "human-authored core idea" work with "let Codex loose" work on the same codebase.
- Learn what breaks, what composes well, and what kind of agent/UI behavior is easy to demo.

The rough working style was:

- I wrote the main direction, core structure, and key pieces of the project.
- Then I let Codex expand the system and push on the edges of the idea.
- Some parts were intentionally left as a stronger Codex experiment than others.
- For example, I did not manually work on the Angular frontend, which makes it a useful artifact for seeing what Codex
  produced on its own.

## Capabilities Explored

This repo is meant to exercise a bunch of A2A and agent-integration behaviors in one place:

- Remote A2A agents exposed as separate services with their own agent cards
- An ADK orchestrator that selectively calls downstream A2A agents instead of always consulting everything
- Routing between multiple agent styles: astrology, tarot, and web-backed search
- Streaming-style task progress updates across the A2A lifecycle
- `input-required` follow-up flow when the orchestrator needs more data before continuing
- Multi-step task continuity via `task_id` and `context_id`
- Agent-card discovery and service-to-service communication over HTTP
- LangChain-based tool use inside an A2A agent (`web_search_agent`)
- ADK orchestrator behavior coordinating remote specialists
- Comparison of two different frontend clients against the same backend task flow
- Containerized deployment of each service to simulate separately deployed agents

## What is included

- `web_search_agent`: A2A agent with LangChain + DuckDuckGo tool.
- `astrology_agent`: A2A agent with synthetic astrology tools.
- `tarot_agent`: A2A streaming tarot agent with delayed card-by-card reveals.
- `orchestrator_agent`: Google ADK agent that orchestrates remote A2A sub-agents.
- `main.py`: root entrypoint
    - `serve` mode: runs orchestrator server
    - `ask` mode: sends one question to orchestrator as a client
- `streamlit_ui/streamlit_app.py`: minimal chat frontend for interacting with the orchestrator
    - supports A2A `input-required` follow-up for missing astrology birth date
- `angular/`: alternative Angular chat frontend with the same A2A capabilities
    - same chat flow, task continuity, progress updates, and follow-up input

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

6. Run Streamlit chat UI (optional)

```bash
uv run --env-file .env streamlit run streamlit_ui/streamlit_app.py
```

7. Run Angular chat UI (optional)

```bash
cd angular
npm install
npm start
```

## One-command startup

Start all four backend services in one terminal:

```bash
./scripts/start_all.sh
```

This starts `web_search_agent`, `astrology_agent`, `tarot_agent`, and `orchestrator_agent`.
Logs are written under `logs/`.

## Docker Compose

Run everything (all agents + both UIs):

```bash
docker compose up --build
```

Each service is built from its own Dockerfile (`<service>/Dockerfile`) to simulate separate deployments.

Endpoints (see `docker-compose.yml` for the full list and ports):

- Web search agent: `http://127.0.0.1:8000`
- Astrology agent: `http://127.0.0.1:8001`
- Tarot agent: `http://127.0.0.1:8002`
- Orchestrator: `http://127.0.0.1:8010`
- Streamlit UI: `http://127.0.0.1:8501`
- Angular UI: `http://127.0.0.1:8502`

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

The orchestrator now uses the ADK remote-agent setup again, so the oracle itself chooses which downstream tools to call
for a request instead of consulting every service by default.

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
- The orchestrator can emit `input-required` when astrology is selected and it needs a birth date that was not already
  provided.
- The Streamlit UI shows the collected task progress in an "A2A task progress" section for each reply.
- The Angular UI mirrors the same task lifecycle and follow-up flow for side-by-side comparison.

## Notes

- This is a starter skeleton intended to be extended.
- Outputs are plain text and intentionally human-readable for demo purposes.
