FROM python:3.12-slim

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir --disable-pip-version-check .

ENV HOST=0.0.0.0 PORT=3000
EXPOSE 3000
CMD ["python", "-m", "unipay_router.server"]
