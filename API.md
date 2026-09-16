# API Reference

**Base URL:** `http://localhost:3000/v1`

**Authentication:** API Key (header: `X-API-Key`)

---

## Payment Intents

### Create Payment Intent

```http
POST /v1/payment-intents
```

**Request:**
```json
{
  "amount": 10000,
  "currency": "INR",
  "receiver_handle": "bob@unipay",
  "sender": {
    "country": "IN",
    "preferred_methods": ["upi", "card"]
  }
}
```

**Response:**
```json
{
  "id": "pi_a1b2c3d4",
  "amount": 10000,
  "currency": "INR",
  "route": {
    "payer_method": "upi",
    "settlement_method": "upi",
    "provider": "Razorpay",
    "amount": 10000,
    "currency": "INR",
    "fee": 10.0,
    "fx_cost": 0,
    "net_received": 9990,
    "success_probability": 0.987,
    "settlement_speed": "instant",
    "score": 0.0037
  },
  "alternatives": [
    {
      "payer_method": "upi",
      "settlement_method": "upi",
      "provider": "Cashfree Payments",
      "fee": 7.5,
      "net_received": 9992.5,
      "score": 0.0073
    }
  ]
}
```

### Get Payment Intent

```http
GET /v1/payment-intents/{id}
```

**Response:**
```json
{
  "id": "pi_a1b2c3d4",
  "amount": 10000,
  "currency": "INR",
  "state": "route_selected",
  "selected_route": { ... }
}
```

---

### Confirm Payment Intent (local simulation)

```http
POST /v1/payment-intents/{id}/confirm
```

This endpoint advances the intent through the payment lifecycle using the
local in-memory simulator. It does **not** contact a bank, payment provider,
or move money. It is intended for UI and integration testing only.

```json
{
  "id": "pi_a1b2c3d4",
  "state": "settled",
  "simulated": true
}
```

---

## Receiver Preferences

### Create/Update Receiver Preferences

```http
POST /v1/receiver-preferences
```

**Request:**
```json
{
  "receiver_id": "bob",
  "handle": "bob@unipay",
  "country": "IN",
  "currency": "INR",
  "preferred_methods": ["upi", "bank_transfer"],
  "rejected_methods": ["wallet"],
  "max_fee_percentage": 0.5,
  "max_fee_absolute": 50.0,
  "settlement_speed": "instant"
}
```

**Response:**
```json
{
  "handle": "bob@unipay",
  "receiver_id": "bob"
}
```

### Resolve Handle

```http
GET /v1/resolve/{handle}
```

**Response:**
```json
{
  "receiver_id": "bob",
  "country": "IN",
  "currency": "INR",
  "preferred_methods": ["upi", "bank_transfer"],
  "rejected_methods": ["wallet"],
  "max_fee_percentage": 0.5,
  "max_fee_absolute": 50.0,
  "settlement_speed_preference": "instant"
}
```

---

## Routes

### List Available Routes

```http
GET /v1/routes?amount=10000&currency=INR&receiver_handle=bob@unipay
```

**Response:**
```json
{
  "routes": [
    {
      "payer_method": "upi",
      "settlement_method": "upi",
      "provider": "Razorpay",
      "fee": 10.0,
      "success_probability": 0.987,
      "score": 0.0037
    }
  ],
  "count": 1
}
```

---

## FX Rates

### Get Exchange Rate

```http
GET /v1/fx-rate?from=USD&to=INR
```

**Response:**
```json
{
  "from": "USD",
  "to": "INR",
  "rate": 83.5,
  "spread": 0.003,
  "source": "live"
}
```

---

## Webhooks

### Handle Provider Webhook

```http
POST /v1/webhooks/{provider}
```

**Providers:** `razorpay`, `cashfree`, `payu`

**Request:** Raw webhook payload from provider

**Response:**
```json
{
  "event": "payment.captured",
  "payment_id": "pay_xxx",
  "provider": "razorpay",
  "status": "captured"
}
```

---

## Payment Graph

### Get Graph Statistics

```http
GET /v1/graph/stats
```

**Response:**
```json
{
  "total_nodes": 34,
  "total_edges": 67,
  "node_types": {
    "currency": 9,
    "provider": 5,
    "method": 8,
    "country": 8,
    "receiver": 2,
    "merchant": 2
  },
  "edge_types": {
    "supports": 42,
    "corridor": 9,
    "located_in": 4,
    "accepts": 10,
    "denominated_in": 2
  }
}
```

---

## Health

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "providers": 5,
  "receivers": 3,
  "payment_intents": 42,
  "graph_nodes": 34,
  "graph_edges": 67
}
```

---

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request — Invalid parameters |
| 404 | Not Found — Resource doesn't exist |
| 422 | Unprocessable Entity — Valid JSON but semantically incorrect |
| 500 | Internal Server Error |

**Error Response Format:**
```json
{
  "error": "Receiver not found: unknown@unipay"
}
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| POST /v1/payment-intents | 100 req/min |
| GET /v1/payment-intents/{id} | 1000 req/min |
| POST /v1/receiver-preferences | 100 req/min |
| GET /v1/resolve/{handle} | 1000 req/min |
| POST /v1/webhooks/* | 1000 req/min |
