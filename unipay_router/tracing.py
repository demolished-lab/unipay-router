"""Optional OpenTelemetry tracing integration.

Tracing remains dependency-free unless OTEL_ENABLED=true and the tracing extra
is installed. The default exporter target is Jaeger's OTLP/HTTP endpoint.
"""
from __future__ import annotations

import os
from contextlib import nullcontext


class Tracing:
    def __init__(self) -> None:
        self.enabled = os.getenv("OTEL_ENABLED", "false").lower() in {"1", "true", "yes"}
        self.tracer = None
        self.propagate = None
        self.trace = None
        if not self.enabled:
            return
        try:
            from opentelemetry import propagate, trace
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            resource = Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", "unipay-router")})
            provider = TracerProvider(resource=resource)
            endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4318/v1/traces")
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
            trace.set_tracer_provider(provider)
            self.tracer = trace.get_tracer("unipay-router")
            self.propagate = propagate
            self.trace = trace
        except ImportError:
            self.enabled = False

    def start_span(self, name: str, headers: dict[str, str]):
        if not self.enabled or self.tracer is None:
            return nullcontext(None)
        carrier = {key.lower(): value for key, value in headers.items()}
        parent = self.propagate.extract(carrier)
        span = self.tracer.start_span(name, context=parent)
        return _SpanContext(span, self.trace.use_span(span, end_on_exit=False))


class _SpanContext:
    def __init__(self, span, context_manager) -> None:
        self.span = span
        self.context_manager = context_manager

    def __enter__(self):
        self.context_manager.__enter__()
        return self.span

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.context_manager.__exit__(exc_type, exc_value, traceback)
        self.span.end()
