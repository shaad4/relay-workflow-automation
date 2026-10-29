# syntax=docker/dockerfile:1
# Build and run this same image in Compose and Kubernetes. Pin a reviewed digest
# for release images; the tag supports both linux/amd64 and linux/arm64.
FROM python:3.12-slim-bookworm AS dependencies
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
RUN python -m venv /opt/venv
COPY requirements.txt ./requirements.txt
# Fail rather than silently require native toolchains on unsupported platforms.
RUN /opt/venv/bin/pip install --only-binary=:all: -r requirements.txt

FROM python:3.12-slim-bookworm AS runtime
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp
RUN groupadd --gid 10001 relay && useradd --uid 10001 --gid 10001 --no-create-home relay
WORKDIR /app
COPY --from=dependencies /opt/venv /opt/venv
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()"]
# Migrations run explicitly, never concurrently in each application replica.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
