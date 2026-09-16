import json
import threading
import urllib.error
import urllib.request

from unipay_router.rate_limiter import InMemoryRateLimiter
from unipay_router.server import UniPayHTTPServer


def test_http_tracing_and_rate_limit_headers():
    server = UniPayHTTPServer(("127.0.0.1", 0))
    server.rate_limiter = InMemoryRateLimiter(limit=1, window_seconds=60)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        request = urllib.request.Request(base + "/health", headers={"X-Request-ID": "test-request", "X-Trace-ID": "trace-123"})
        with urllib.request.urlopen(request) as response:
            assert response.status == 200
            assert response.headers["X-Request-ID"] == "test-request"
            assert response.headers["X-Trace-ID"] == "trace-123"
            assert response.headers["X-RateLimit-Remaining"] == "0"

        try:
            urllib.request.urlopen(base + "/health")
        except urllib.error.HTTPError as response:
            assert response.code == 429
            body = json.loads(response.read())
            assert body["error"] == "rate limit exceeded"
            assert int(response.headers["Retry-After"]) >= 1
        else:
            raise AssertionError("expected HTTP 429")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
