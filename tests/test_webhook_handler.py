import base64
import hashlib
import hmac
import json

from unipay_router.webhook_handler import WebhookEvent, WebhookHandler


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode()


def test_razorpay_valid_signature_and_normalization(monkeypatch):
    secret = "razorpay-test-secret"
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", secret)
    handler = WebhookHandler()
    payload = json.dumps({
        "event": "payment.captured",
        "payload": {"payment": {"entity": {"id": "pay_123", "amount": 1000, "currency": "INR", "status": "captured"}}},
    }).encode()
    signature = _b64(hmac.new(secret.encode(), payload, hashlib.sha256).digest())
    event = handler.process("razorpay", payload, {"x-razorpay-signature": signature})
    assert event is not None
    assert event.event == WebhookEvent.PAYMENT_CAPTURED
    assert event.payment_id == "pay_123"


def test_razorpay_invalid_signature_is_rejected(monkeypatch):
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "secret")
    handler = WebhookHandler()
    payload = b'{"event":"payment.captured","payload":{}}'
    assert handler.process("razorpay", payload, {"x-razorpay-signature": "wrong"}) is None


def test_cashfree_valid_signature_includes_timestamp(monkeypatch):
    secret = "cashfree-test-secret"
    timestamp = "1700000000000"
    monkeypatch.setenv("CASHFREE_WEBHOOK_SECRET", secret)
    handler = WebhookHandler()
    payload = json.dumps({
        "type": "PAYMENT_SUCCESS",
        "data": {"order": {"order_id": "order_123", "order_amount": 250, "order_currency": "INR"}, "payment": {"cf_payment_id": "cf_123", "payment_status": "SUCCESS"}},
    }).encode()
    signature = _b64(hmac.new(secret.encode(), timestamp.encode() + payload, hashlib.sha256).digest())
    event = handler.process("cashfree", payload, {"x-webhook-signature": signature, "x-webhook-timestamp": timestamp})
    assert event is not None
    assert event.event == WebhookEvent.PAYMENT_CAPTURED
    assert event.payment_id == "cf_123"


def test_cashfree_wrong_timestamp_signature_is_rejected(monkeypatch):
    secret = "cashfree-test-secret"
    monkeypatch.setenv("CASHFREE_WEBHOOK_SECRET", secret)
    handler = WebhookHandler()
    payload = b'{"type":"PAYMENT_SUCCESS","data":{}}'
    signature = _b64(hmac.new(secret.encode(), b"correct" + payload, hashlib.sha256).digest())
    assert handler.process("cashfree", payload, {"x-webhook-signature": signature, "x-webhook-timestamp": "wrong"}) is None


def test_payu_success_is_normalized_without_signature_requirement(monkeypatch):
    monkeypatch.delenv("PAYU_WEBHOOK_SECRET", raising=False)
    handler = WebhookHandler()
    payload = json.dumps({"status": "success", "transaction_details": {"mihpayid": "payu_123", "amount": "100", "currency": "INR"}}).encode()
    event = handler.process("payu", payload, {})
    assert event is not None
    assert event.event == WebhookEvent.PAYMENT_CAPTURED
    assert event.payment_id == "payu_123"


def test_unknown_provider_is_rejected():
    assert WebhookHandler().process("unknown", b"{}", {}) is None
