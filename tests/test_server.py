import json
import threading
import urllib.request

from unipay_router.server import UniPayHTTPServer


def test_http_health_and_payment_intent():
    server = UniPayHTTPServer(("127.0.0.1", 0))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        receiver_payload = json.dumps({
            "receiver_id": "bob",
            "handle": "bob@unipay",
            "preferred_methods": ["upi"],
        }).encode()
        receiver_request = urllib.request.Request(
            base + "/v1/receiver-preferences", data=receiver_payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(receiver_request) as response:
            assert response.status == 200

        with urllib.request.urlopen(base + "/health") as response:
            assert response.status == 200
            assert json.loads(response.read())["status"] == "ok"

        payload = json.dumps({
            "amount": 1000,
            "currency": "INR",
            "receiver_handle": "bob@unipay",
            "sender": {"preferred_methods": ["upi"]},
        }).encode()
        request = urllib.request.Request(
            base + "/v1/payment-intents", data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request) as response:
            result = json.loads(response.read())
            assert response.status == 200
            assert result["amount"] == 1000
            assert result["route"]
    finally:
        server.shutdown()
        server.server_close()
