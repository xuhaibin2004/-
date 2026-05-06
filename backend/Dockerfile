FROM docker.1ms.run/python:3.11-slim AS base

WORKDIR /app

COPY pyproject.toml .
RUN env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
    pip install --no-cache-dir \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.32.0" \
    "sqlalchemy[asyncio]>=2.0.0" \
    "asyncpg>=0.30.0" \
    "pgvector>=0.3.0" \
    "redis>=5.0.0" \
    "httpx>=0.27.0" \
    "pydantic>=2.0.0" \
    "pydantic-settings>=2.0.0" \
    "python-multipart>=0.0.9" \
    "websockets>=13.0" \
    "alembic>=1.13.0" \
    "openai>=1.50.0" \
    "anthropic>=0.35.0" \
    "numpy>=1.26.0" \
    "celery>=5.4.0"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
