FROM python:3.14-slim-bookworm@sha256:48b13b003dda20b16f9442b8475aa05fe21bf6579a8c881db92ffb4d8fd20f83

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.11.16

COPY pyproject.toml uv.lock ./

RUN uv sync \
    --frozen \
    --no-dev

ENV PATH="/app/.venv/bin:$PATH"

COPY app ./app
COPY specs ./specs
COPY THIRD_PARTY_NOTICES.md LICENSE ./
COPY licenses ./licenses

RUN useradd \
    --create-home \
    --uid 10001 \
    appuser

USER appuser

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
