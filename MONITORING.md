# Proxy and Monitoring

## Alerting and notifications

Prometheus now loads [alert rules](monitoring/prometheus/alerts.yml) for
availability, 5xx/4xx error rates, p95 latency, and rate-limit saturation. It
sends firing and resolved alerts to the optional Alertmanager service.

Configure notification channels with environment variables:

```bash
ALERT_EMAIL_TO='ops@example.com'
ALERT_CRITICAL_EMAIL_TO='oncall@example.com'
ALERT_WEBHOOK_URL='https://hooks.example.com/unipay'
ALERT_CRITICAL_WEBHOOK_URL='https://hooks.example.com/unipay-critical'
SMTP_SMARTHOST='smtp.example.com:587'
SMTP_FROM='unipay-alerts@example.com'
SMTP_USERNAME='smtp-user'
SMTP_PASSWORD='smtp-password'
```

The default file contains safe placeholder destinations. Replace them before
using email or webhook delivery. Alertmanager is available at
`http://localhost:9093` in the local monitoring profile.

The Alertmanager configuration is in
`monitoring/alertmanager/alertmanager.yml`.

## Distributed tracing with OpenTelemetry and Jaeger

Tracing is optional and disabled by default so the zero-cost simulator remains
dependency-free. Install the tracing extra and enable OTLP export:

```bash
pip install -e '.[tracing]'
export OTEL_ENABLED=true
export OTEL_SERVICE_NAME=unipay-router
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318/v1/traces
python -m unipay_router.server
```

The HTTP server creates spans for incoming requests, extracts W3C propagation
headers when supplied, and exports spans to Jaeger over OTLP/HTTP. With Compose,
start the Jaeger profile together with the router:

```bash
OTEL_ENABLED=true \
docker compose --profile tracing up --build
```

Jaeger’s UI is available at `http://localhost:16686`. The Compose service also
exposes OTLP/HTTP on port 4318 and OTLP/gRPC on port 4317. Set
`OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318/v1/traces` inside Compose.

Tracing is best-effort: if the optional OpenTelemetry packages are not
installed, the application automatically falls back to no-op spans.

## Nginx reverse proxy with SSL termination

The repository includes an optional Nginx profile. Nginx listens on ports 80 and
443, redirects HTTP to HTTPS, terminates TLS, forwards tracing headers, and
proxies API traffic to `unipay-router:3000`.

### Local self-signed certificate

For local testing only:

```bash
mkdir -p infra/nginx/certs
openssl req -x509 -nodes -newkey rsa:2048 -days 30 \
  -keyout infra/nginx/certs/privkey.pem \
  -out infra/nginx/certs/fullchain.pem \
  -subj '/CN=localhost'
```

Start the proxy:

```bash
docker compose --profile proxy up --build
```

Open `https://localhost/`. Browsers will warn because the certificate is
self-signed. Do not use a self-signed certificate for production.

### Production certificates

Replace the two certificate files with a certificate issued for your real
hostname by a trusted CA such as Let’s Encrypt. Keep private keys outside Git.
The included Nginx configuration passes `X-Request-ID`, `X-Trace-ID`,
`X-Forwarded-For`, and `X-Forwarded-Proto` to the application.

The Nginx `/metrics` location is restricted to loopback by default. Prometheus
in this Compose stack scrapes the application directly on the internal Docker
network, so it does not need to traverse Nginx.

## Prometheus exporter

The router exposes Prometheus text format at:

```text
GET /metrics
```

Metrics include:

- `unipay_http_requests_total{method,path,status}`
- `unipay_http_request_duration_seconds_bucket`
- `unipay_http_request_duration_seconds_sum`
- `unipay_http_request_duration_seconds_count`
- `unipay_http_in_flight_requests`

Dynamic paths are normalized to keep metric cardinality bounded. If
`METRICS_API_KEY` is set, requests to `/metrics` must include that value in the
`X-API-Key` header. Keep Prometheus on a trusted network or protect it with a
proxy when exposing metrics externally.

Test locally:

```bash
curl http://localhost:3000/metrics
```

## Prometheus and Grafana

Start the optional monitoring profile:

```bash
GRAFANA_ADMIN_PASSWORD='use-a-strong-password' \
  docker compose --profile monitoring up --build
```

Endpoints:

- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3001`

Grafana is preconfigured with:

- A Prometheus datasource at `http://prometheus:9090`
- A provisioned **UniPay Router Overview** dashboard
- Request rate, error rate, p95 latency, route/status breakdown, in-flight
  requests, total requests, and HTTP 429 counts

Files:

- [Prometheus configuration](monitoring/prometheus/prometheus.yml)
- [Grafana dashboard](monitoring/grafana/dashboards/unipay-router.json)
- [Grafana datasource provisioning](monitoring/grafana/provisioning/datasources/prometheus.yml)
- [Grafana dashboard provisioning](monitoring/grafana/provisioning/dashboards/dashboards.yml)

## Combined local stack

Run Redis-backed rate limiting, Nginx, Prometheus, and Grafana together:

```bash
UNIPAY_API_KEY='change-me' \
RATE_LIMIT_BACKEND=redis \
RATE_LIMIT_REQUESTS=100 \
GRAFANA_ADMIN_PASSWORD='use-a-strong-password' \
  docker compose --profile redis --profile proxy --profile monitoring up --build
```

This configuration is intended for development and staging. Before production,
use managed TLS renewal, a managed Redis service, durable metrics storage,
secret management, firewall rules, authentication for Grafana/Prometheus, and
alerts for error rate, latency, and rate-limit saturation.
