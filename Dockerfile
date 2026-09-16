FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=3000

WORKDIR /app

COPY pyproject.toml README.md ./
COPY unipay_router ./unipay_router
RUN pip install --no-cache-dir --disable-pip-version-check . \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

USER appuser
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3000/health', timeout=3)"

CMD ["python", "-m", "unipay_router.server"]
