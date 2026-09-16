# Routing Algorithm

## The Scoring Function

The core routing optimization is:

```
R* = argmin_R (C_R + L_R + F_R + X_R + Q_R)
```

Where each component is normalized to 0-1 scale:

| Weight | Component | Description |
|--------|-----------|-------------|
| 0.35 | C_R | Cost: (fee + fx_cost) / amount |
| 0.15 | L_R | Latency: min(latency_ms / 5000, 1) |
| 0.25 | F_R | Failure risk: 1 - success_probability |
| 0.15 | X_R | FX cost: fx_cost / amount |
| 0.10 | Q_R | Compliance/risk penalty: 0-1 risk score |

**Lower score = better route.**

```mermaid
graph TD
    A[Payment Intent] --> B[Generate Candidates]
    B --> C[For each route R]
    C --> D[Calculate C_R]
    C --> E[Calculate L_R]
    C --> F[Calculate F_R]
    C --> G[Calculate X_R]
    C --> H[Calculate Q_R]
    D --> I[Weighted Sum]
    E --> I
    F --> I
    G --> I
    H --> I
    I --> J{compliance_ok?}
    J -->|No| K[infinity - rejected]
    J -->|Yes| L{receiver_accepts?}
    L -->|No| K
    L -->|Yes| M[Score = 0.35*C + 0.15*L + 0.25*F + 0.15*X + 0.10*Q]
    M --> N[Sort ascending]
    N --> O[Return top K routes]
```

## Candidate Generation

```mermaid
graph LR
    A[Sender Methods] --> B[Receiver Methods]
    B --> C[Intersection]
    C --> D[UPI candidates]
    C --> E[Card candidates]
    C --> F[Net Banking candidates]
    D --> G[Per-provider: Razorpay, Cashfree, PayU]
    E --> G
    F --> G
    G --> H[All candidates]
    H --> I[Score each]
    I --> J[Return sorted]
```

## Constraint Filtering

Before scoring, candidates are filtered:

```python
# Receiver preference filtering
if route.payment_method not in receiver.preferred_methods:
    route.receiver_accepts = False

if route.payment_method in receiver.rejected_methods:
    route.receiver_accepts = False

if route.fee > receiver.max_fee_absolute:
    route.receiver_accepts = False

if (route.fee / route.amount) > (receiver.max_fee_percentage / 100):
    route.receiver_accepts = False
```

## Cross-Border Routing

```mermaid
graph TD
    A[Cross-border Payment] --> B{Same currency?}
    B -->|Yes| C[Direct route]
    B -->|No| D[FX conversion]
    D --> E[Get live rate]
    E --> F[Apply spread]
    F --> G[Calculate X_R]
    G --> H[Total cost includes FX]
    C --> I[Score route]
    H --> I
```

## Failure Recovery

```mermaid
sequenceDiagram
    participant R as Router
    participant H as Hyperswitch
    participant P1 as Primary Provider
    participant P2 as Fallback Provider

    R->>H: Attempt payment via P1
    H->>P1: Process payment
    P1-->>H: FAILED
    H->>R: Webhook (failed)
    R->>R: Find next best route
    R->>H: Attempt payment via P2
    H->>P2: Process payment
    P2-->>H: SUCCESS
    H->>R: Webhook (captured)
```

## Route Selection Priority

1. **Receiver constraints** (hard filter) — methods, fees, speed
2. **Compliance** (hard filter) — country regulations, risk
3. **Failure risk** (high weight) — success rate is king
4. **Cost** (high weight) — total fee + FX
5. **Latency** (lower weight) — speed matters but not at any cost
