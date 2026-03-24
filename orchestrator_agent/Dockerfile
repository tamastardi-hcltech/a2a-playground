FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN pip install --no-cache-dir \
    a2a-sdk[http-server]>=0.3.25 \
    google-adk>=1.27.1 \
    langchain-openai>=1.1.11 \
    litellm>=1.75.5 \
    uvicorn>=0.42.0

COPY . /app/orchestrator_agent
