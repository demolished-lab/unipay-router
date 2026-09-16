# Deployment

## Zero-cost local deployment

The included service is a local development and integration-test MVP. It uses
Python's standard library and in-memory state, so it needs no database,
Hyperswitch instance, provider credentials, or paid API.

### Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m unipay_router.server
```

The API listens on `http://localhost:3000`.

### Docker Compose

Docker is optional. The Compose file builds only the router image:

```bash
docker compose up --build
```

Stop it with:

```bash
docker compose down
```

### Configuration

| Variable | Default | Purpose |
|---|---:|---|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `3000` | HTTP port |
| `UNIPAY_API_KEY` | empty | If set, require `X-API-Key` on API requests |
| `CORS_ORIGIN` | `*` | CORS allow-origin value |
| `LOG_LEVEL` | `info` | Set to `quiet` to suppress request logs |

Example:

```bash
UNIPAY_API_KEY=change-this-local-key PORT=3000 python -m unipay_router.server
```

## Important limitations

This MVP stores receiver preferences and payment intents in process memory;
restarting the server clears them. The simulated confirmation endpoint does not
contact banks or providers and does not move money. It exists for front-end and
integration testing.

Before any real-money deployment, add durable storage, TLS termination,
per-user authentication and authorization, request rate limiting, signed
webhook verification, idempotency keys, provider sandbox testing, audit logs,
reconciliation, regulated payment-provider contracts, and a security/compliance
review. Do not put real card data into this application.

## Production evolution path

1. Keep the deterministic routing engine and replace the in-memory stores with
   PostgreSQL or another durable database.
2. Add an adapter per regulated payment provider and keep provider credentials
   outside source control.
3. Make payment creation and webhook processing idempotent.
4. Add observability, retry queues, reconciliation, and operational alerts.
5. Deploy behind HTTPS with restricted network access and tested backups.
