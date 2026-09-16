# Receiver Preferences

## Overview

Receiver preferences are the core differentiator. Every receiver defines how they want to get paid.

```mermaid
graph TD
    A[Receiver @bob] --> B[Preferences]
    B --> C[Methods: UPI, Net Banking]
    B --> D[Max Fee: 0.5% or Rs.50]
    B --> E[Currency: INR]
    B --> F[Speed: Instant settlement]
    B --> G[Rejected: Wallets]
```

## Preference Schema

```json
{
  "receiver_id": "bob",
  "handle": "bob@unipay",
  "country": "IN",
  "currency": "INR",
  "preferred_methods": ["upi", "net_banking"],
  "rejected_methods": ["wallet"],
  "max_fee_percentage": 0.5,
  "max_fee_absolute": 50.0,
  "settlement_speed": "instant"
}
```

## Filtering Logic

```mermaid
flowchart TD
    A[Route Candidate] --> B{Method in preferred?}
    B -->|No| C[Reject]
    B -->|Yes| D{Method in rejected?}
    D -->|Yes| C
    D -->|No| E{Fee <= max_absolute?}
    E -->|No| C
    E -->|Yes| F{Fee% <= max_percentage?}
    F -->|No| C
    F -->|Yes| G{Settlement speed OK?}
    G -->|No| C
    G -->|Yes| H[Route accepted]
```

## Handle Resolution

```mermaid
sequenceDiagram
    participant Sender
    participant Router
    participant Store

    Sender->>Router: Pay bob@unipay
    Router->>Store: Lookup bob@unipay
    Store-->>Router: Receiver preferences
    Router->>Router: Filter routes by preferences
```

## Multi-Currency Receivers

A receiver can accept multiple currencies:

```json
{
  "receiver_id": "alice",
  "handle": "alice@unipay",
  "country": "IN",
  "currency": "INR",
  "preferred_methods": ["upi", "visa", "mastercard"],
  "accepted_currencies": ["INR", "USD", "EUR"],
  "max_fee_percentage": 1.0,
  "settlement_speed": "t+1"
}
```

## Privacy Levels

| Level | Description |
|-------|-------------|
| Public | Handle visible to all, preferences public |
| Registered | Handle must be known, preferences private |
| Private | No public handle, direct API only |
