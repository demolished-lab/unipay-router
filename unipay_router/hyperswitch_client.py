"""Hyperswitch API client — talks to Hyperswitch server for payment operations."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

try:
    import httpx
except ImportError:
    import json
    import urllib.request
    httpx = None


@dataclass
class HyperswitchConfig:
    base_url: str = "http://localhost:8080"
    api_key: str = ""
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> HyperswitchConfig:
        return cls(
            base_url=os.getenv("HYPERSWITCH_URL", "http://localhost:8080"),
            api_key=os.getenv("HYPERSWITCH_API_KEY", ""),
        )


class HyperswitchClient:
    """Client for Hyperswitch payment orchestration server."""

    def __init__(self, config: HyperswitchConfig | None = None) -> None:
        self.config = config or HyperswitchConfig.from_env()
        self._base = self.config.base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"API-Key {self.config.api_key}",
        }

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        url = f"{self._base}{path}"
        if urlparse(url).scheme not in {"http", "https"}:
            raise ValueError("Hyperswitch URL must use http or https")
        if httpx:
            resp = httpx.request(
                method, url, json=body, headers=self._headers(),
                timeout=self.config.timeout,
            )
            return resp.json()
        else:
            data = json.dumps(body).encode() if body else None
            req = urllib.request.Request(
                url, data=data, headers=self._headers(), method=method,
            )
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:  # nosec B310 - scheme is allowlisted above
                return json.loads(resp.read())

    # ── Payment Intents ──────────────────────────────────────────────────────

    def create_payment_intent(
        self,
        amount: int,
        currency: str = "INR",
        description: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """Create a payment intent via Hyperswitch."""
        body = {
            "amount": amount,
            "currency": currency,
            "confirm": False,
            "capture_method": "automatic",
        }
        if description:
            body["description"] = description
        if metadata:
            body["metadata"] = metadata
        return self._request("POST", "/payments", body)

    def confirm_payment(self, payment_id: str) -> dict:
        """Confirm (authorize) a payment."""
        return self._request("POST", f"/payments/{payment_id}/confirm")

    def capture_payment(self, payment_id: str, amount: int | None = None) -> dict:
        """Capture an authorized payment."""
        body = {}
        if amount:
            body["amount_to_capture"] = amount
        return self._request("POST", f"/payments/{payment_id}/capture", body)

    def get_payment(self, payment_id: str) -> dict:
        """Retrieve payment details."""
        return self._request("GET", f"/payments/{payment_id}")

    def list_payments(self, limit: int = 10, offset: int = 0) -> dict:
        """List payments with pagination."""
        return self._request("GET", f"/payments?limit={limit}&offset={offset}")

    # ── Refunds ──────────────────────────────────────────────────────────────

    def create_refund(self, payment_id: str, amount: int, reason: str | None = None) -> dict:
        """Create a refund for a payment."""
        body = {"amount": amount}
        if reason:
            body["reason"] = reason
        return self._request("POST", f"/payments/{payment_id}/refund", body)

    def get_refund(self, payment_id: str, refund_id: str) -> dict:
        """Get refund status."""
        return self._request("GET", f"/payments/{payment_id}/refunds/{refund_id}")

    # ── Routing ──────────────────────────────────────────────────────────────

    def get_routing_algorithm(self, merchant_id: str) -> dict:
        """Get the current routing algorithm for a merchant."""
        return self._request("GET", f"/routing_algorithm/{merchant_id}")

    def create_routing_algorithm(self, merchant_id: str, algorithm: dict) -> dict:
        """Create or update a routing algorithm."""
        return self._request("POST", "/routing_algorithm", {
            "merchant_id": merchant_id,
            **algorithm,
        })

    # ── Connectors ───────────────────────────────────────────────────────────

    def list_connectors(self) -> dict:
        """List configured payment connectors."""
        return self._request("GET", "/connectors")

    def create_connector(self, connector_config: dict) -> dict:
        """Add a new payment connector."""
        return self._request("POST", "/connectors", connector_config)

    # ── Webhooks ─────────────────────────────────────────────────────────────

    def register_webhook(self, url: str, events: list[str] | None = None) -> dict:
        """Register a webhook endpoint."""
        body = {"url": url}
        if events:
            body["events"] = events
        return self._request("POST", "/webhooks", body)

    # ── Health ───────────────────────────────────────────────────────────────

    def health_check(self) -> dict:
        """Check Hyperswitch server health."""
        try:
            return self._request("GET", "/health")
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def is_healthy(self) -> bool:
        """Check if Hyperswitch is reachable."""
        try:
            health = self.health_check()
            return health.get("status") == "ok"
        except Exception:
            return False
