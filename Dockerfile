# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm

ARG APP_VERSION=dev
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="Data Visualization Tool" \
      org.opencontainers.image.source="https://github.com/Matte13/Data-Visualization-Tool" \
      org.opencontainers.image.version="$APP_VERSION" \
      org.opencontainers.image.revision="$VCS_REF"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt requirements-postgres.txt ./
# The optional build-only CA supports managed proxies without baking them into
# the image. Normal Docker Desktop / GitHub builds do not require this secret.
RUN --mount=type=secret,id=proxy_ca \
    if [ -s /run/secrets/proxy_ca ]; then \
      PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir -r requirements.txt -r requirements-postgres.txt; \
    else pip install --no-cache-dir -r requirements.txt -r requirements-postgres.txt; fi \
    && useradd --uid 10001 --create-home explorer
COPY --chown=explorer:explorer app ./app
COPY --chown=explorer:explorer web ./web
COPY --chown=explorer:explorer data ./data
RUN mkdir /app/runtime && chown explorer:explorer /app/runtime
USER explorer
EXPOSE 8000
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=6s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/ready', timeout=5)" || exit 1
CMD ["python", "-m", "app.server", "--host", "0.0.0.0", "--port", "8000"]
