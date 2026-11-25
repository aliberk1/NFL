FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    HOME=/tmp NFL_DB_PATH=/data/curated/nfl.duckdb NFL_STATE_DIR=/data/state NFL_DEMO_MODE=1
WORKDIR /srv/nfl

COPY requirements-app.lock ./
RUN pip install --require-hashes -r requirements-app.lock

COPY app ./app
COPY pipelines ./pipelines
COPY docker ./docker
RUN useradd --system --uid 10001 nfl && mkdir -p /data && chown nfl /data

ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION
LABEL org.opencontainers.image.version=$APP_VERSION

USER 10001
VOLUME /data
EXPOSE 8501
HEALTHCHECK --interval=15s --timeout=10s --start-period=60s --retries=3 \
    CMD ["python", "-m", "app.healthcheck"]
ENTRYPOINT ["sh", "docker/entrypoint.sh"]
CMD ["sh", "docker/start-ui.sh"]
