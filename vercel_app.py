"""Vercel WSGI adapter for the zero-dependency UniPay API.

Render can run the normal threaded server. Vercel needs a request/response
entrypoint instead, so this file translates WSGI requests into UniPayAPI calls.
"""
from __future__ import annotations

import json
import os
from urllib.parse import parse_qs, unquote, urlsplit

from unipay_router.api import UniPayAPI

api = UniPayAPI()


def _json(start_response, status: str, value: dict):
    body = json.dumps(value, separators=(",", ":")).encode()
    start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(body)))])
    return [body]


def _body(environ) -> dict:
    length = int(environ.get("CONTENT_LENGTH") or 0)
    if length > 1_048_576:
        raise ValueError("request body is too large")
    raw = environ["wsgi.input"].read(length) if length else b"{}"
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON body must be an object")
    return value


def app(environ, start_response):
    if os.getenv("UNIPAY_API_KEY", "").strip() and environ.get("HTTP_X_API_KEY", "") != os.getenv("UNIPAY_API_KEY"):
        return _json(start_response, "401 Unauthorized", {"error": "invalid or missing API key"})
    method = environ.get("REQUEST_METHOD", "GET")
    parsed = urlsplit(environ.get("PATH_INFO", "/"))
    path = parsed.path.rstrip("/") or "/"
    try:
        if method == "GET" and path in ("/", "/health"):
            return _json(start_response, "200 OK", api.health_check())
        if method == "GET" and path.startswith("/v1/payment-intents/"):
            result = api.get_payment_intent(unquote(path.rsplit("/", 1)[1]))
            return _json(start_response, "404 Not Found" if "error" in result else "200 OK", result)
        if method == "GET" and path.startswith("/v1/resolve/"):
            result = api.resolve_handle(unquote(path.rsplit("/", 1)[1]))
            return _json(start_response, "404 Not Found" if "error" in result else "200 OK", result)
        if method == "GET" and path == "/v1/routes":
            query = parse_qs(parsed.query)
            result = api.list_routes({"amount": float(query.get("amount", [0])[0]), "currency": query.get("currency", ["INR"])[0].upper(), "receiver_handle": query.get("receiver_handle", [""])[0]})
            return _json(start_response, "400 Bad Request" if "error" in result else "200 OK", result)
        if method == "GET" and path == "/v1/fx-rate":
            query = parse_qs(parsed.query)
            return _json(start_response, "200 OK", api.get_fx_rate(query.get("from", ["USD"])[0].upper(), query.get("to", ["INR"])[0].upper()))
        if method == "GET" and path == "/v1/graph/stats":
            return _json(start_response, "200 OK", api.get_graph_stats())
        if method == "POST":
            body = _body(environ)
            if path == "/v1/payment-intents":
                result = api.create_payment_intent(body)
            elif path.startswith("/v1/payment-intents/") and path.endswith("/confirm"):
                result = api.confirm_payment_intent(unquote(path.split("/")[-2]))
            elif path == "/v1/receiver-preferences":
                result = api.create_receiver_preference(body)
            elif path.startswith("/v1/webhooks/"):
                provider = path.rsplit("/", 1)[1]
                raw = json.dumps(body).encode()
                headers = {key[5:].lower().replace("_", "-"): value for key, value in environ.items() if key.startswith("HTTP_")}
                result = api.handle_webhook(provider, raw, headers)
            else:
                result = {"error": "not found"}
            error = result.get("error", "")
            status = "404 Not Found" if "not found" in error else ("400 Bad Request" if error else "200 OK")
            return _json(start_response, status, result)
        return _json(start_response, "404 Not Found", {"error": "not found"})
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return _json(start_response, "400 Bad Request", {"error": str(exc)})
    except Exception as exc:
        return _json(start_response, "500 Internal Server Error", {"error": "internal server error", "detail": str(exc)})
