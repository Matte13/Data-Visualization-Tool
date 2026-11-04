# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm

ARG APP_VERSION=dev
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="Data Visualization Tool" \
      org.opencontainers.image.source="https://github.com/Matte13/Data-Visualization-Tool" \
      org.opencontainers.image.version="$APP_VERSION" \
      org.opencontainers.image.revision="$VCS_REF"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 STORAGE_BACKEND=azuresql
WORKDIR /app
COPY requirements.txt requirements-postgres.txt requirements-azuresql.txt ./
# The optional build-only CA supports managed proxies without baking them into
# the image. Normal Docker Desktop / GitHub builds do not require this secret.
RUN --mount=type=secret,id=proxy_ca,mode=0444 \
    if [ -s /run/secrets/proxy_ca ]; then \
      export PIP_CERT=/run/secrets/proxy_ca CURL_CA_BUNDLE=/run/secrets/proxy_ca; \
      printf 'Acquire::https::CaInfo "/run/secrets/proxy_ca";\n' > /etc/apt/apt.conf.d/99-build-proxy; \
    fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl --fail --silent --show-error --location https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb --output /tmp/packages-microsoft-prod.deb \
    && dpkg -i /tmp/packages-microsoft-prod.deb \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc \
    && pip install --no-cache-dir -r requirements.txt -r requirements-postgres.txt -r requirements-azuresql.txt \
    && rm -rf /var/lib/apt/lists/* /tmp/packages-microsoft-prod.deb /etc/apt/apt.conf.d/99-build-proxy \
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
