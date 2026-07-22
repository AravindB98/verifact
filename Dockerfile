FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY web ./web

RUN pip install --no-cache-dir .

# Non-root runtime user
RUN useradd --create-home verifact
USER verifact

ENV VERIFACT_HOST=0.0.0.0 \
    VERIFACT_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request,sys; \
  sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health').status==200 else 1)"

CMD ["verifact", "serve", "--host", "0.0.0.0", "--port", "8000"]
