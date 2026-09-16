"""Zero-dependency HTTP API for local UniPay Router development.

This server deliberately uses only Python's standard library. It is suitable for
local demos and tests; production deployments should put TLS, authentication,
and durable storage in front of it.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .api import UniPayAPI
from .metrics import MetricsRegistry
from .rate_limiter import RateLimitDecision, build_rate_limiter
from .tracing import Tracing


class JsonLogFormatter(logging.Formatter):
    """Format access and application records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "trace_id", "method", "path", "status", "duration_ms", "client_ip"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, separators=(",", ":"))


logger = logging.getLogger("unipay_router")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    logger.addHandler(handler)
configured_level = os.getenv("LOG_LEVEL", "INFO").upper()
logger.setLevel(logging.CRITICAL + 1 if configured_level == "QUIET" else configured_level)
logger.propagate = False


class UniPayHTTPServer(ThreadingHTTPServer):
    """Threaded server carrying one in-memory API instance."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], api: UniPayAPI | None = None):
        self.api = api or UniPayAPI()
        self.rate_limiter = build_rate_limiter()
        self.metrics = MetricsRegistry()
        self.tracing = Tracing()
        super().__init__(address, UniPayRequestHandler)


class UniPayRequestHandler(BaseHTTPRequestHandler):
    server: UniPayHTTPServer
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        # Access records are emitted by _send as structured JSON.
        return

    def _request_context(self) -> bool:
        self._request_started = time.perf_counter()
        self.server.metrics.begin()
        self._span_context = self.server.tracing.start_span(
            f"{self.command} {urlparse(self.path).path}", dict(self.headers)
        )
        self._span = self._span_context.__enter__()
        incoming = self.headers.get("X-Request-ID", "").strip()
        self.request_id = self._safe_trace_id(incoming) or str(uuid.uuid4())
        self.trace_id = self._safe_trace_id(self.headers.get("X-Trace-ID", "")) or self.request_id
        forwarded = self.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip()
        self.client_ip = forwarded or self.client_address[0]
        api_key = self.headers.get("X-API-Key", "")
        decision = self.server.rate_limiter.check(api_key or self.client_ip)
        self._rate_limit = decision
        if not decision.allowed:
            self._send(429, {"error": "rate limit exceeded", "retry_after": decision.retry_after})
            return False
        return True

    @staticmethod
    def _safe_trace_id(value: str) -> str:
        value = value[:128]
        return value if value and re.fullmatch(r"[A-Za-z0-9._:-]+", value) else ""

    def _authorized(self) -> bool:
        expected = os.getenv("UNIPAY_API_KEY", "").strip()
        return not expected or self.headers.get("X-API-Key", "") == expected

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", os.getenv("CORS_ORIGIN", "*"))
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("X-Request-ID", getattr(self, "request_id", str(uuid.uuid4())))
        self.send_header("X-Trace-ID", getattr(self, "trace_id", getattr(self, "request_id", "")))
        decision: RateLimitDecision | None = getattr(self, "_rate_limit", None)
        if decision:
            self.send_header("X-RateLimit-Limit", str(decision.limit))
            self.send_header("X-RateLimit-Remaining", str(decision.remaining))
            self.send_header("X-RateLimit-Reset", str(decision.reset_at))
            if status == 429:
                self.send_header("Retry-After", str(decision.retry_after))
        self.end_headers()
        self.wfile.write(body)
        duration_seconds = time.perf_counter() - getattr(self, "_request_started", time.perf_counter())
        self.server.metrics.observe(self.command, urlparse(self.path).path, status, duration_seconds)
        logger.info(
            "http_request",
            extra={
                "request_id": getattr(self, "request_id", ""),
                "trace_id": getattr(self, "trace_id", ""),
                "method": self.command,
                "path": urlparse(self.path).path,
                "status": status,
                "duration_ms": round((time.perf_counter() - getattr(self, "_request_started", time.perf_counter())) * 1000, 2),
                "client_ip": getattr(self, "client_ip", ""),
            },
        )
        self._finish_span(status)

    def _finish_span(self, status: int) -> None:
        span = getattr(self, "_span", None)
        if span is not None:
            span.set_attribute("http.request.method", self.command)
            span.set_attribute("http.response.status_code", status)
            span.set_attribute("url.path", urlparse(self.path).path)
            self._span_context.__exit__(None, None, None)
            self._span = None

    def _send_metrics(self) -> None:
        body = self.server.metrics.render().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Request-ID", self.request_id)
        self.send_header("X-Trace-ID", self.trace_id)
        self.end_headers()
        self.wfile.write(body)
        self.server.metrics.observe(
            self.command,
            "/metrics",
            200,
            time.perf_counter() - getattr(self, "_request_started", time.perf_counter()),
        )
        self._finish_span(200)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_048_576:
            raise ValueError("request body is too large")
        raw = self.rfile.read(length) if length else b"{}"
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON body must be an object")
        return value

    def do_OPTIONS(self) -> None:
        if not self._request_context():
            return
        self._send(204, {})

    def do_GET(self) -> None:
        if not self._request_context():
            return
        if not self._authorized():
            self._send(401, {"error": "invalid or missing API key"})
            return
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        if path == "/metrics":
            metrics_key = os.getenv("METRICS_API_KEY", "").strip()
            if metrics_key and self.headers.get("X-API-Key", "") != metrics_key:
                self._send(401, {"error": "invalid or missing metrics API key"})
                return
            self._send_metrics()
            return
        if path in ("", "/health"):
            self._send(200, self.server.api.health_check())
            return
        if path.startswith("/v1/payment-intents/"):
            result = self.server.api.get_payment_intent(unquote(path.rsplit("/", 1)[1]))
            self._send(404 if "error" in result else 200, result)
            return
        if path.startswith("/v1/resolve/"):
            result = self.server.api.resolve_handle(unquote(path.rsplit("/", 1)[1]))
            self._send(404 if "error" in result else 200, result)
            return
        if path == "/v1/routes":
            query = parse_qs(parsed.query)
            request = {
                "amount": float(query.get("amount", [0])[0]),
                "currency": query.get("currency", ["INR"])[0].upper(),
                "receiver_handle": query.get("receiver_handle", [""])[0],
            }
            self._send(200, self.server.api.list_routes(request))
            return
        if path == "/v1/fx-rate":
            query = parse_qs(parsed.query)
            self._send(200, self.server.api.get_fx_rate(
                query.get("from", ["USD"])[0].upper(), query.get("to", ["INR"])[0].upper()
            ))
            return
        if path == "/v1/graph/stats":
            self._send(200, self.server.api.get_graph_stats())
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if not self._request_context():
            return
        if not self._authorized():
            self._send(401, {"error": "invalid or missing API key"})
            return
        path = urlparse(self.path).path.rstrip("/")
        try:
            body = self._read_json()
            if path == "/v1/payment-intents":
                result = self.server.api.create_payment_intent(body)
            elif path.startswith("/v1/payment-intents/") and path.endswith("/confirm"):
                payment_id = unquote(path.split("/")[-2])
                result = self.server.api.confirm_payment_intent(payment_id)
            elif path == "/v1/receiver-preferences":
                result = self.server.api.create_receiver_preference(body)
            else:
                match = re.fullmatch(r"/v1/webhooks/([^/]+)", path)
                if not match:
                    self._send(404, {"error": "not found"})
                    return
                result = self.server.api.handle_webhook(
                    match.group(1), json.dumps(body).encode(), dict(self.headers)
                )
            status = 400 if "error" in result else 200
            error = result.get("error", "")
            if error.endswith("not found") or "not found:" in error:
                status = 404
            self._send(status, result)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._send(400, {"error": str(exc)})
        except Exception as exc:  # keep the local API JSON-shaped on unexpected input
            self._send(500, {"error": "internal server error", "detail": str(exc)})


def run(host: str = "0.0.0.0", port: int = 3000) -> None:  # nosec B104 - required for container hosting
    """Run the local API until interrupted."""
    server = UniPayHTTPServer((host, port))
    print(f"UniPay Router listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run(os.getenv("HOST", "0.0.0.0"), int(os.getenv("PORT", "3000")))  # nosec B104 - required for container hosting
