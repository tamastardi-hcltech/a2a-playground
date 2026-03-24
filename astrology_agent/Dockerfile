FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN pip install --no-cache-dir \
    a2a-sdk[http-server]>=0.3.25 \
    langchain>=1.2.12 \
    langchain-openai>=1.1.11 \
    uvicorn>=0.42.0

COPY . /app/astrology_agent
