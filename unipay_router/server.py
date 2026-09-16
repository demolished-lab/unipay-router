"""Zero-dependency HTTP API for local UniPay Router development.

This server deliberately uses only Python's standard library. It is suitable for
local demos and tests; production deployments should put TLS, authentication,
and durable storage in front of it.
"""
from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .api import UniPayAPI


class UniPayHTTPServer(ThreadingHTTPServer):
    """Threaded server carrying one in-memory API instance."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], api: UniPayAPI | None = None):
        self.api = api or UniPayAPI()
        super().__init__(address, UniPayRequestHandler)


class UniPayRequestHandler(BaseHTTPRequestHandler):
    server: UniPayHTTPServer
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        if os.getenv("LOG_LEVEL", "info").lower() != "quiet":
            super().log_message(format, *args)

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", os.getenv("CORS_ORIGIN", "*"))
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_048_576:
            raise ValueError("request body is too large")
        raw = self.rfile.read(length) if length else b"{}"
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON body must be an object")
        return value

    def _authorized(self) -> bool:
        expected = os.getenv("UNIPAY_API_KEY", "").strip()
        return not expected or self.headers.get("X-API-Key", "") == expected

    def do_OPTIONS(self) -> None:
        self._send(204, {})

    def do_GET(self) -> None:
        if not self._authorized():
            self._send(401, {"error": "invalid or missing API key"})
            return
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
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
