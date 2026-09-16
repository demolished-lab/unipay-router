import threading
import urllib.request

from unipay_router.metrics import MetricsRegistry
from unipay_router.server import UniPayHTTPServer


def test_metrics_registry_renders_request_counter_and_histogram():
    registry = MetricsRegistry()
    registry.begin()
    registry.observe("GET", "/v1/payment-intents/example", 200, 0.01)
    text = registry.render()
    assert 'unipay_http_requests_total{method="GET",path="/v1/payment-intents/:id",status="200"} 1' in text
    assert "unipay_http_request_duration_seconds_bucket" in text
    assert "unipay_http_in_flight_requests 0" in text


def test_metrics_endpoint_returns_prometheus_text():
    server = UniPayHTTPServer(("127.0.0.1", 0))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urllib.request.urlopen(base + "/health") as response:
            assert response.status == 200
        with urllib.request.urlopen(base + "/metrics") as response:
            body = response.read().decode()
            assert response.headers["Content-Type"].startswith("text/plain")
            assert "unipay_http_requests_total" in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
