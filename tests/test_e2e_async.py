import asyncio
import json
import threading
import uuid

import httpx
import pytest
import pytest_asyncio

from unipay_router.server import UniPayHTTPServer


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def api_client():
    server = UniPayHTTPServer(("127.0.0.1", 0))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    await asyncio.sleep(0.01)
    async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{server.server_port}") as client:
        yield client
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


async def register_receiver(client: httpx.AsyncClient, handle: str) -> None:
    response = await client.post(
        "/v1/receiver-preferences",
        json={"receiver_id": handle.split("@", 1)[0], "handle": handle, "preferred_methods": ["upi"]},
    )
    assert response.status_code == 200


async def test_complete_payment_intent_lifecycle(api_client: httpx.AsyncClient):
    handle = f"e2e-{uuid.uuid4().hex[:8]}@unipay"
    await register_receiver(api_client, handle)

    resolved = await api_client.get(f"/v1/resolve/{handle}")
    assert resolved.status_code == 200
    assert resolved.json()["receiver_id"] == handle.split("@", 1)[0]

    created = await api_client.post(
        "/v1/payment-intents",
        json={"amount": 1250, "currency": "INR", "receiver_handle": handle, "sender": {"preferred_methods": ["upi"]}},
    )
    assert created.status_code == 200
    intent_id = created.json()["id"]
    assert created.json()["route"]["settlement_method"] == "upi"

    listed = await api_client.get("/v1/routes", params={"amount": 1250, "currency": "INR", "receiver_handle": handle})
    assert listed.status_code == 200
    assert listed.json()["count"] >= 1

    before = await api_client.get(f"/v1/payment-intents/{intent_id}")
    assert before.json()["state"] == "created"

    confirmed = await api_client.post(f"/v1/payment-intents/{intent_id}/confirm", json={})
    assert confirmed.status_code == 200
    assert confirmed.json()["state"] == "settled"
    assert confirmed.json()["simulated"] is True

    after = await api_client.get(f"/v1/payment-intents/{intent_id}")
    assert after.json()["state"] == "settled"


async def test_supporting_read_endpoints(api_client: httpx.AsyncClient):
    health = await api_client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    fx = await api_client.get("/v1/fx-rate", params={"from": "USD", "to": "INR"})
    assert fx.status_code == 200
    assert fx.json()["rate"] > 0

    graph = await api_client.get("/v1/graph/stats")
    assert graph.status_code == 200
    assert graph.json()["total_nodes"] > 0


async def test_provider_webhook_normalization(api_client: httpx.AsyncClient):
    razorpay = await api_client.post(
        "/v1/webhooks/razorpay",
        json={"event": "payment.captured", "payload": {"payment": {"entity": {"id": "pay_e2e", "status": "captured"}}}},
    )
    assert razorpay.status_code == 200
    assert razorpay.json()["provider"] == "razorpay"

    cashfree = await api_client.post(
        "/v1/webhooks/cashfree",
        json={"type": "PAYMENT_SUCCESS", "data": {"order": {"order_id": "order_e2e"}, "payment": {"cf_payment_id": "cf_e2e"}}},
    )
    assert cashfree.status_code == 200
    assert cashfree.json()["event"] == "payment.captured"

    payu = await api_client.post(
        "/v1/webhooks/payu",
        content=json.dumps({"status": "success", "transaction_details": {"mihpayid": "payu_e2e"}}),
        headers={"Content-Type": "application/json"},
    )
    assert payu.status_code == 200
    assert payu.json()["payment_id"] == "payu_e2e"


async def test_validation_and_not_found_errors(api_client: httpx.AsyncClient):
    invalid = await api_client.post("/v1/payment-intents", json={"amount": 0, "currency": "INR", "receiver_handle": "missing@unipay"})
    assert invalid.status_code == 400
    assert "positive finite" in invalid.json()["error"]

    missing = await api_client.get("/v1/payment-intents/not-a-real-id")
    assert missing.status_code == 404
    assert "not found" in missing.json()["error"].lower()

    unknown = await api_client.post("/v1/webhooks/no-such-provider", json={})
    assert unknown.status_code == 400
