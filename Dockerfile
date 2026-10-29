FROM python:3.13-slim-bookworm AS builder
WORKDIR /build
COPY requirements.lock.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r requirements.lock.txt

FROM python:3.13-slim-bookworm
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app commerce ./commerce
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app frontend ./frontend
COPY --chown=app:app alembic.ini .
RUN mkdir .data && chown app:app .data
USER app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready', timeout=3)"
CMD ["python", "-m", "commerce.serve"]
