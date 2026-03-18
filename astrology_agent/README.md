# Astrology Agent

Entertainment-only astrology agent. It can infer zodiac sign from birth date and generate a mysterious daily reading.

## Run

```bash
uv run --env-file astrology_agent/.env python -m astrology_agent.main
```

Default port is `8001`. Override with:

```bash
A2A_PORT=8001 uv run --env-file astrology_agent/.env python -m astrology_agent.main
```

## Notes

- No external astrology API required (dummy tool output).
- Uses `OPENAI_API_KEY` for the LLM.
- Optional: `ASTROLOGY_TEMPERATURE` (default `1.3`).
