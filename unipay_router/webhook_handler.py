"""Webhook Handler — processes incoming webhooks from payment providers.

Handles signature verification and event normalization across providers.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import urllib.request
from dataclasses import dataclass
from enum import Enum

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]


class WebhookEvent(str, Enum):
    PAYMENT_AUTHORIZED = "payment.authorized"
    PAYMENT_CAPTURED = "payment.captured"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_REFUNDED = "payment.refunded"
    PAYMENT_DISPUTED = "payment.disputed"
    SETTLEMENT_COMPLETED = "settlement.completed"


@dataclass
class WebhookPayload:
    event: WebhookEvent
    payment_id: str
    provider: str
    amount: int | None = None
    currency: str | None = None
    status: str | None = None
    metadata: dict | None = None
    raw: dict | None = None


class WebhookHandler:
    """Processes webhooks from Razorpay, Cashfree, PayU, etc."""

    def __init__(self) -> None:
        self._processors: dict[str, callable] = {
            "razorpay": self._process_razorpay,
            "cashfree": self._process_cashfree,
            "payu": self._process_payu,
        }
        self._webhook_secrets: dict[str, str] = {
            "razorpay": os.getenv("RAZORPAY_WEBHOOK_SECRET", ""),
            "cashfree": os.getenv("CASHFREE_WEBHOOK_SECRET", ""),
            "payu": os.getenv("PAYU_WEBHOOK_SECRET", ""),
        }

    def process(self, provider: str, payload: bytes, headers: dict[str, str]) -> WebhookPayload | None:
        """Process a webhook from a provider."""
        processor = self._processors.get(provider)
        if not processor:
            return None
        return processor(payload, headers)

    # ── Signature Verification ───────────────────────────────────────────────

    def verify_razorpay(self, payload: bytes, signature: str, secret: str) -> bool:
        """Verify Razorpay webhook signature (HMAC-SHA256)."""
        if not secret:
            return True  # Skip verification if no secret configured
        expected = hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).digest()
        import base64
        expected_b64 = base64.b64encode(expected).decode()
        return hmac.compare_digest(expected_b64, signature)

    def verify_cashfree(self, payload: bytes, signature: str, timestamp: str, secret: str) -> bool:
        """Verify Cashfree webhook signature (HMAC-SHA256)."""
        if not secret:
            return True
        signed_payload = timestamp.encode() + payload
        expected = hmac.new(
            secret.encode(), signed_payload, hashlib.sha256
        ).digest()
        import base64
        expected_b64 = base64.b64encode(expected).decode()
        return hmac.compare_digest(expected_b64, signature)

    # ── Razorpay Processing ──────────────────────────────────────────────────

    def _process_razorpay(self, payload: bytes, headers: dict[str, str]) -> WebhookPayload | None:
        signature = headers.get("x-razorpay-signature", "")
        secret = self._webhook_secrets.get("razorpay", "")

        if not self.verify_razorpay(payload, signature, secret):
            return None

        data = json.loads(payload)
        event = data.get("event", "")
        payment_entity = data.get("payload", {}).get("payment", {}).get("entity", {})

        event_map = {
            "payment.authorized": WebhookEvent.PAYMENT_AUTHORIZED,
            "payment.captured": WebhookEvent.PAYMENT_CAPTURED,
            "payment.failed": WebhookEvent.PAYMENT_FAILED,
            "payment.refunded": WebhookEvent.PAYMENT_REFUNDED,
            "payment.dispute.created": WebhookEvent.PAYMENT_DISPUTED,
        }

        return WebhookPayload(
            event=event_map.get(event, WebhookEvent.PAYMENT_FAILED),
            payment_id=payment_entity.get("id", ""),
            provider="razorpay",
            amount=payment_entity.get("amount"),
            currency=payment_entity.get("currency"),
            status=payment_entity.get("status"),
            metadata=payment_entity.get("notes"),
            raw=data,
        )

    # ── Cashfree Processing ──────────────────────────────────────────────────

    def _process_cashfree(self, payload: bytes, headers: dict[str, str]) -> WebhookPayload | None:
        signature = headers.get("x-webhook-signature", "")
        timestamp = headers.get("x-webhook-timestamp", "")
        secret = self._webhook_secrets.get("cashfree", "")

        if not self.verify_cashfree(payload, signature, timestamp, secret):
            return None

        data = json.loads(payload)
        event = data.get("type", "")
        order = data.get("data", {}).get("order", {})
        payment = data.get("data", {}).get("payment", {})

        event_map = {
            "PAYMENT_AUTHORIZED": WebhookEvent.PAYMENT_AUTHORIZED,
            "PAYMENT_SUCCESS": WebhookEvent.PAYMENT_CAPTURED,
            "PAYMENT_FAILED": WebhookEvent.PAYMENT_FAILED,
            "PAYMENT_REFUND_CREATED": WebhookEvent.PAYMENT_REFUNDED,
        }

        return WebhookPayload(
            event=event_map.get(event, WebhookEvent.PAYMENT_FAILED),
            payment_id=payment.get("cf_payment_id", order.get("order_id", "")),
            provider="cashfree",
            amount=order.get("order_amount"),
            currency=order.get("order_currency"),
            status=payment.get("payment_status"),
            raw=data,
        )

    # ── PayU Processing ──────────────────────────────────────────────────────

    def _process_payu(self, payload: bytes, headers: dict[str, str]) -> WebhookPayload | None:
        data = json.loads(payload)
        status = data.get("status", "")
        transaction = data.get("transaction_details", {})

        event_map = {
            "success": WebhookEvent.PAYMENT_CAPTURED,
            "failure": WebhookEvent.PAYMENT_FAILED,
            "pending": WebhookEvent.PAYMENT_AUTHORIZED,
        }

        return WebhookPayload(
            event=event_map.get(status, WebhookEvent.PAYMENT_FAILED),
            payment_id=transaction.get("payuMoneyId", transaction.get("mihpayid", "")),
            provider="payu",
            amount=transaction.get("amount"),
            currency=transaction.get("currency"),
            status=status,
            raw=data,
        )

    # ── Outgoing Webhook ─────────────────────────────────────────────────────

    def send_outgoing(self, url: str, payload: dict, secret: str | None = None) -> bool:
        """Send an outgoing webhook to a merchant endpoint."""
        body = json.dumps(payload).encode()
        headers = {"Content-Type": "application/json"}

        if secret:
            signature = hmac.new(secret.encode(), body, hashlib.sha256).digest()
            import base64
            headers["X-Signature"] = base64.b64encode(signature).decode()

        try:
            if httpx:
                resp = httpx.post(url, json=payload, headers=headers, timeout=10.0)
                return resp.status_code < 400
            else:
                req = urllib.request.Request(url, data=body, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return resp.status < 400
        except Exception:
            return False
