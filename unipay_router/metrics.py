"""Small Prometheus text exporter with no runtime dependencies."""
from __future__ import annotations

import re
import threading
from collections import defaultdict


class MetricsRegistry:
    """Thread-safe request counters and latency histograms."""

    BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: defaultdict[tuple[str, str, int], int] = defaultdict(int)
        self._durations: defaultdict[tuple[str, str], list[int]] = defaultdict(lambda: [0] * (len(self.BUCKETS) + 1))
        self._duration_sum: defaultdict[tuple[str, str], float] = defaultdict(float)
        self._in_flight = 0

    @staticmethod
    def normalize_path(path: str) -> str:
        path = re.sub(r"/[0-9a-f]{8}-[0-9a-f-]{27,}", "/:id", path, flags=re.IGNORECASE)
        if path.startswith("/v1/payment-intents/"):
            return "/v1/payment-intents/:id"
        if path.startswith("/v1/resolve/"):
            return "/v1/resolve/:handle"
        if path.startswith("/v1/webhooks/"):
            return "/v1/webhooks/:provider"
        return path or "/"

    def begin(self) -> None:
        with self._lock:
            self._in_flight += 1

    def observe(self, method: str, path: str, status: int, duration_seconds: float) -> None:
        normalized = self.normalize_path(path)
        key = (method, normalized)
        with self._lock:
            self._in_flight = max(0, self._in_flight - 1)
            self._requests[(method, normalized, status)] += 1
            self._duration_sum[key] += duration_seconds
            buckets = self._durations[key]
            for index, bound in enumerate(self.BUCKETS):
                if duration_seconds <= bound:
                    buckets[index] += 1
            buckets[-1] += 1

    def render(self) -> str:
        lines = [
            "# HELP unipay_http_requests_total Total HTTP requests by method, path, and status.",
            "# TYPE unipay_http_requests_total counter",
        ]
        with self._lock:
            for (method, path, status), value in sorted(self._requests.items()):
                lines.append(f'unipay_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {value}')
            lines.extend([
                "# HELP unipay_http_request_duration_seconds HTTP request latency histogram.",
                "# TYPE unipay_http_request_duration_seconds histogram",
            ])
            for (method, path), buckets in sorted(self._durations.items()):
                for index, count in enumerate(buckets[:-1]):
                    bound = self.BUCKETS[index]
                    lines.append(f'unipay_http_request_duration_seconds_bucket{{method="{method}",path="{path}",le="{bound}"}} {count}')
                lines.append(f'unipay_http_request_duration_seconds_bucket{{method="{method}",path="{path}",le="+Inf"}} {buckets[-1]}')
                lines.append(f'unipay_http_request_duration_seconds_sum{{method="{method}",path="{path}"}} {self._duration_sum[(method, path)]:.9f}')
                lines.append(f'unipay_http_request_duration_seconds_count{{method="{method}",path="{path}"}} {buckets[-1]}')
            lines.extend([
                "# HELP unipay_http_in_flight_requests Current requests being processed.",
                "# TYPE unipay_http_in_flight_requests gauge",
                f"unipay_http_in_flight_requests {self._in_flight}",
            ])
        return "\n".join(lines) + "\n"
