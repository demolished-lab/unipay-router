# Universal Payment Router

**Sender pays how they want. Receiver receives how they want.**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Hyperswitch](https://img.shields.io/badge/built%20on-Hyperswitch-orange.svg)](https://github.com/juspay/hyperswitch)

## Architecture

```mermaid
graph TB
    subgraph "UniPay Router"
        API[REST API]
        RE[Routing Engine]
        RP[Receiver Preferences]
        PG[Payment Graph]
        FX[FX Engine]
        WH[Webhook Handler]
        REC[Reconciliation]
    end

    subgraph "Hyperswitch Server"
        HS[Hyperswitch Core]
        EUCLID[Euclid DSL Router]
        CG[Constraint Graph]
    end

    subgraph "Payment Providers"
        RZ[Razorpay]
        CF[Cashfree]
        PU[PayU]
    end

    subgraph "External"
        UPI[UPI/NPCI]
        CARD[Card Networks]
        BANK[Banks]
        FXAPI[FX Rate APIs]
    end

    Sender[Sender] -->|Pay| API
    API --> RE
    API --> RP
    RE --> HS
    HS --> EUCLID --> CG
    CG --> RZ
    CG --> CF
    CG --> PU
    RZ --> UPI
    RZ --> CARD
    CF --> UPI
    CF --> BANK
    PU --> UPI
    PU --> CARD
    WH -->|Webhooks| RZ
    WH -->|Webhooks| CF
    WH -->|Webhooks| PU
    FX --> FXAPI
    RP -->|Resolve| Receiver[Receiver]
    PG -->|Graph| RE
    REC -->|Reconcile| API
```

## How It Works

```mermaid
sequenceDiagram
    participant Sender
    participant Router as UniPay Router
    participant Hyperswitch
    participant Provider as Razorpay/Cashfree
    participant Receiver

    Sender->>Router: "Pay Rs.1000 to bob@unipay"
    Router->>Router: Resolve bob's preferences
    Router->>Hyperswitch: Find routes (UPI, Card, Bank)
    Hyperswitch->>Hyperswitch: Apply Euclid DSL rules
    Hyperswitch-->>Router: Ranked routes
    Router->>Router: Filter by receiver preferences
    Router->>Router: Score routes (cost, speed, reliability)
    Router-->>Sender: Best route + alternatives
    Sender->>Router: Confirm payment
    Router->>Hyperswitch: Create payment intent
    Hyperswitch->>Provider: Route to cheapest provider
    Provider-->>Hyperswitch: Payment status
    Hyperswitch-->>Router: Webhook
    Router->>Receiver: Funds received
```

## Quick Start

```bash
# Clone the repo
git clone https://github.com/your-org/unipay-router.git
cd unipay-router

# Start with Docker Compose (or run `python -m unipay_router.server`)
docker compose up --build

# Register a receiver
curl -X POST http://localhost:3000/v1/receiver-preferences \
  -H "Content-Type: application/json" \
  -d '{"receiver_id":"bob","handle":"bob@unipay","preferred_methods":["upi"]}'

# Create a payment intent
curl -X POST http://localhost:3000/v1/payment-intents \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 10000,
    "currency": "INR",
    "receiver_handle": "bob@unipay",
    "sender": {
      "country": "IN",
      "preferred_methods": ["upi", "card"]
    }
  }'
```

### Zero-cost local MVP

The router runs without Hyperswitch, a database, provider credentials, or paid
APIs. It uses deterministic in-memory provider profiles for route selection,
which is suitable for local development and demos. Python 3.10+ is the only
runtime requirement:

```shell
python -m venv .venv
. .venv/bin/activate
pip install -e .
python -m unipay_router.server
```

In a second terminal, register a receiver and request a route:

```shell
curl -X POST http://localhost:3000/v1/receiver-preferences \
  -H 'Content-Type: application/json' \
  -d '{"receiver_id":"bob","handle":"bob@unipay","preferred_methods":["upi"]}'

curl -X POST http://localhost:3000/v1/payment-intents \
  -H 'Content-Type: application/json' \
  -d '{"amount":1000,"currency":"INR","receiver_handle":"bob@unipay","sender":{"preferred_methods":["upi"]}}'
```

Docker is optional and uses the included local-only Compose file:

```shell
docker compose up --build
```

This MVP does not move real money. Real payment acceptance requires regulated
provider accounts, credentials, webhook verification, durable storage, and a
security/compliance review before production use.

## Features

- **Universal Routing**: UPI, Cards, Net Banking, Wallets, PayPal, Bank Transfer
- **Receiver Preferences**: Receivers define how they want to get paid
- **Intelligent Scoring**: `R* = argmin(C + L + F + X + Q)` — cost, latency, failure risk, FX, compliance
- **Failure Recovery**: Automatic retry with alternative providers
- **Payment Graph**: Grows with every receiver, creating network effects
- **Cross-Border**: USD/EUR/GBP/SGD/AED to INR with live FX rates
- **Reconciliation**: Unified view across all providers (the "boring" moat)
- **Built on Hyperswitch**: 43k+ stars, 120+ connectors, production-tested

## Provider Support

| Provider | UPI | Cards | Net Banking | Wallet | Status |
|----------|-----|-------|-------------|--------|--------|
| Razorpay | ✅ | ✅ | ✅ | ✅ | Sandbox Ready |
| Cashfree | ✅ | ✅ | ✅ | ✅ | Sandbox Ready |
| PayU | ✅ | ✅ | ✅ | ✅ | Sandbox Ready |

## Comparison: UniPay Router vs Hyperswitch Alone

| Feature | Hyperswitch | UniPay Router |
|---------|-------------|---------------|
| Routing | Merchant-centric | Receiver-centric |
| Identity | API keys per merchant | Universal `@handle` identity |
| Preferences | Merchant defines rules | Receiver defines constraints |
| Payment graph | None | Grows with every receiver |
| Cross-border | Provider-specific | Intelligent FX routing |

## Documentation

- [Architecture](ARCHITECTURE.md) — System design and data flow
- [API Reference](API.md) — Full REST API documentation
- [Routing Algorithm](ROUTING.md) — Scoring function and constraint graph
- [Provider Integration](PROVIDERS.md) — Sandbox setup for each provider
- [Receiver Preferences](RECEIVER-PREFERENCES.md) — Preference system design
- [Payment Graph](PAYMENT-GRAPH.md) — Graph model and network effects
- [Deployment](DEPLOYMENT.md) — Docker, cloud, local setup
- [Security](SECURITY.md) — PCI compliance, API key handling
- [Contributing](CONTRIBUTING.md) — Development setup and guidelines

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

Built on [Hyperswitch](https://github.com/juspay/hyperswitch) (Apache 2.0).
