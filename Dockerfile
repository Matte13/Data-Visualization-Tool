FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt requirements-postgres.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-postgres.txt \
    && useradd --uid 10001 --create-home explorer
COPY --chown=explorer:explorer app ./app
COPY --chown=explorer:explorer web ./web
COPY --chown=explorer:explorer data ./data
RUN mkdir /app/runtime && chown explorer:explorer /app/runtime
USER explorer
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)" || exit 1
CMD ["python", "-m", "app.server", "--host", "0.0.0.0", "--port", "8000"]
