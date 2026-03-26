FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN pip install --no-cache-dir \
    a2a-sdk[http-server]>=0.3.25 \
    httpx>=0.28.1 \
    streamlit>=1.44.0

COPY . /app/streamlit_ui
