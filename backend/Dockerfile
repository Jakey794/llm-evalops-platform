FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN pip install uv \
    && uv sync --locked --no-dev --no-install-project \
    && useradd --create-home --uid 10001 appuser

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts

RUN chmod +x scripts/start.sh

USER appuser

EXPOSE 8000

CMD ["sh", "./scripts/start.sh"]
