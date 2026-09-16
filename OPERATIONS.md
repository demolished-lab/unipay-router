# Operations and Container Deployment

## Rate limiting

The HTTP server applies a sliding-window rate limit to every request. The
identifier is the `X-API-Key` when present, otherwise the client IP address.
Responses include:

```text
X-RateLimit-Limit
X-RateLimit-Remaining
X-RateLimit-Reset
```

When the limit is exceeded, the server returns HTTP `429` with a `Retry-After`
header and a JSON error body.

The default backend is zero-cost, thread-safe in-memory storage:

```text
RATE_LIMIT_BACKEND=memory
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60
```

The memory backend is per process. Use Redis when multiple replicas must share
a limit:

```bash
pip install -e '.[redis]'
export RATE_LIMIT_BACKEND=redis
export REDIS_URL=redis://localhost:6379/0
```

Redis uses atomic fixed-window counters. It is not required for local
single-process development.

## Structured logs and tracing

Each HTTP request emits one JSON log record to stdout. Example fields include:

```json
{"timestamp":"2026-09-16T23:00:00Z","level":"info","logger":"unipay_router","message":"http_request","request_id":"...","trace_id":"...","method":"GET","path":"/health","status":200,"duration_ms":1.4,"client_ip":"127.0.0.1"}
```

The server returns and accepts:

- `X-Request-ID`: request correlation identifier; generated when absent.
- `X-Trace-ID`: trace correlation identifier; defaults to the request ID.

Pass these headers from an API gateway or frontend to correlate logs across
services. `X-Forwarded-For` is used for the client address when the server is
behind a trusted reverse proxy.

Set `LOG_LEVEL=quiet` only affects legacy server logging behavior; structured
request records are controlled by the Python logger level. Use `LOG_LEVEL=WARNING`
or `ERROR` to reduce normal request output.

## Docker

Build and run the router directly:

```bash
docker build -t unipay-router:local .
docker run --rm -p 3000:3000 \
  -e UNIPAY_API_KEY='change-me' \
  -e RATE_LIMIT_REQUESTS=100 \
  unipay-router:local
```

The image:

- Binds to `0.0.0.0:3000` by default.
- Runs as a non-root user.
- Includes a Docker health check for `/health`.
- Emits JSON logs to stdout for container log collection.

## Docker Compose: in-memory mode

This is the simplest zero-cost mode:

```bash
UNIPAY_API_KEY=change-me docker compose up --build
```

Verify it:

```bash
curl -H 'X-API-Key: change-me' http://localhost:3000/health
```

## Docker Compose: Redis-backed mode

Start the router and the local Redis service using the optional profile:

```bash
UNIPAY_API_KEY=change-me \
RATE_LIMIT_BACKEND=redis \
REDIS_URL=redis://redis:6379/0 \
docker compose --profile redis up --build
```

The Redis profile is useful for local multi-process testing. Redis is not
required by the default image and has no persistence configured in this
zero-cost development Compose file. Do not use this configuration as a
production data store.

## Production boundary

This repository remains a development/sandbox router. Before production use,
add durable storage, trusted proxy configuration, provider-specific webhook
idempotency, secret rotation, TLS termination, metrics, alerting, and a managed
Redis deployment if shared rate limits are required.
