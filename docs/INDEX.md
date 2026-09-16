# Documentation Index

All documentation for the Universal Payment Router.

## Core

- [README](README.md) — Project overview and quick start
- [Architecture](ARCHITECTURE.md) — System design, data flow, and component diagrams
- [API Reference](API.md) — REST API endpoints and examples
- [Postman Collection](../postman/UniPay-Router.postman_collection.json) — Importable requests for all API endpoints
- [OpenAPI Specification](../openapi/openapi.json) — OpenAPI 3.1 schema for Swagger and client generation
- [Interactive Swagger UI](swagger.html) — Browser-based API explorer for the OpenAPI specification

## Components

- [Routing Algorithm](ROUTING.md) — Scoring function and constraint graph
- [Receiver Preferences](RECEIVER-PREFERENCES.md) — Preference system design and filtering
- [Payment Graph](PAYMENT-GRAPH.md) — Graph model, corridors, and network effects
- [Provider Integration](PROVIDERS.md) — Sandbox setup for Razorpay, Cashfree, PayU

## Operations

- [Deployment](DEPLOYMENT.md) — Docker, cloud, and local setup
- [Free Hosting Quickstart](../FREE-HOSTING.md) — Deploy on Render Free or Vercel Functions
- [Load Testing](../LOAD-TESTING.md) — Locust workloads and benchmark guidance
- [Async End-to-End Tests](../tests/test_e2e_async.py) — pytest-asyncio and httpx API workflow coverage
- [Operations](../OPERATIONS.md) — Rate limiting, tracing, JSON logs, Docker, and Compose
- [Security](SECURITY.md) — PCI compliance, API keys, and best practices

## Development

- [Contributing](CONTRIBUTING.md) — Development setup and guidelines
- [License](../LICENSE) — Apache 2.0
