# Tarot Stream Agent

A2A streaming tarot agent with an explicit draw tool and per-card interpretation.

## Run

```bash
uv run --env-file tarot_agent/.env python -m tarot_agent.main
```

Default port is `8002`. Override with:

```bash
A2A_PORT=8002 uv run --env-file tarot_agent/.env python -m tarot_agent.main
```

## Streaming Behavior

- Uses a `draw_next_tarot_card` tool internally.
- Sends multiple `working` status updates, one per card with interpretation.
- Sends a final `completed` message with the full spread.

## Optional Env Vars

- `TAROT_CARD_COUNT` (default `3`)
- `TAROT_DELAY_MIN_SEC` (default `5`)
- `TAROT_DELAY_MAX_SEC` (default `15`)
