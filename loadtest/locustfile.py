"""Locust workload for UniPay Router.

Start the router first, then run:
  locust -f loadtest/locustfile.py --host http://127.0.0.1:3000

This workload is intentionally safe for the local simulator. It never calls a
real payment provider and uses unique receiver handles per virtual user.
"""
from __future__ import annotations

import json
import uuid

from locust import HttpUser, between, task


class UniPayUser(HttpUser):
    wait_time = between(0.2, 1.0)

    def on_start(self) -> None:
        self.handle = f"loadtest-{uuid.uuid4().hex[:10]}@unipay"
        self.api_headers = {"Content-Type": "application/json"}
        response = self.client.post(
            "/v1/receiver-preferences",
            headers=self.api_headers,
            json={
                "receiver_id": self.handle.split("@", 1)[0],
                "handle": self.handle,
                "preferred_methods": ["upi"],
            },
            name="POST /v1/receiver-preferences (setup)",
        )
        response.raise_for_status()

    @task(5)
    def health(self) -> None:
        self.client.get("/health", name="GET /health")

    @task(4)
    def list_routes(self) -> None:
        self.client.get(
            "/v1/routes",
            params={"amount": "1000", "currency": "INR", "receiver_handle": self.handle},
            name="GET /v1/routes",
        )

    @task(3)
    def create_intent_and_confirm(self) -> None:
        response = self.client.post(
            "/v1/payment-intents",
            headers=self.api_headers,
            json={
                "amount": 1000,
                "currency": "INR",
                "receiver_handle": self.handle,
                "sender": {"country": "IN", "preferred_methods": ["upi"]},
            },
            name="POST /v1/payment-intents",
        )
        if response.ok:
            payment_id = response.json().get("id")
            if payment_id:
                self.client.get(f"/v1/payment-intents/{payment_id}", name="GET /v1/payment-intents/:id")
                self.client.post(
                    f"/v1/payment-intents/{payment_id}/confirm",
                    headers=self.api_headers,
                    data=json.dumps({}),
                    name="POST /v1/payment-intents/:id/confirm",
                )

    @task(2)
    def fx_rate(self) -> None:
        self.client.get("/v1/fx-rate", params={"from": "USD", "to": "INR"}, name="GET /v1/fx-rate")

    @task(1)
    def webhook_fixture(self) -> None:
        payload = {
            "event": "payment.captured",
            "payload": {"payment": {"entity": {"id": f"pay_{uuid.uuid4().hex[:12]}", "amount": 1000, "currency": "INR", "status": "captured"}}},
        }
        self.client.post(
            "/v1/webhooks/razorpay",
            headers=self.api_headers,
            json=payload,
            name="POST /v1/webhooks/razorpay",
        )
