# Payment Graph

## Concept

A payment graph models the flow of money as a network:

```mermaid
graph TB
    subgraph "Nodes"
        C1[USD]
        C2[INR]
        C3[EUR]
        P1[Razorpay]
        P2[Cashfree]
        P3[PayU]
        M1[UPI]
        M2[Visa]
        M3[Mastercard]
        R1[Bob]
        R2[Alice]
        CO1[India]
        CO2[US]
    end

    subgraph "Edges"
        E1[Razorpay -- supports --> UPI]
        E2[Razorpay -- supports --> Visa]
        E3[Cashfree -- supports --> UPI]
        E4[PayU -- supports --> UPI]
        E5[UPI -- located_in --> India]
        E6[Visa -- denominated_in --> USD]
        E7[USD -- converts_to --> INR]
        E8[Bob -- accepts --> UPI]
        E9[Alice -- accepts --> Visa]
    end

    P1 --> E1
    P1 --> E2
    P2 --> E3
    P3 --> E4
    M1 --> E5
    M2 --> E6
    C1 --> E7
    R1 --> E8
    R2 --> E9
```

## Node Types

| Type | Examples | Count |
|------|----------|-------|
| Currency | INR, USD, EUR, GBP, SGD, AED | 6+ |
| Provider | Razorpay, Cashfree, PayU | 3+ |
| Payment Method | UPI, Visa, Mastercard, RuPay, Net Banking | 5+ |
| Country | India, US, UK, UAE | 4+ |
| Receiver | @bob, @alice, @merchant1 | Dynamic |
| Merchant | Store1, Store2 | Dynamic |

## Edge Types

| Edge | From | To | Meaning |
|------|------|----|---------|
| supports | Provider | Method | Provider can process this method |
| located_in | Method | Country | Method works in this country |
| denominated_in | Method | Currency | Method operates in this currency |
| converts_to | Currency | Currency | FX conversion possible |
| accepts | Receiver | Method | Receiver accepts this method |

## Corridor: The Key Path

A corridor is the complete path money can take:

```
USD -> Visa -> Razorpay -> INR -> UPI -> Bob
```

```mermaid
graph LR
    A[USD] -->|converts_to| B[INR]
    B -->|denominated_in| C[UPI]
    C -->|supports| D[Razorpay]
    D -->|located_in| E[India]
    E -->|accepts| F[Bob]
```

## Network Effects

```mermaid
graph TD
    A[1 Receiver] --> B[1 Corridor]
    B --> C[Low Value]
    C --> D[10 Receivers]
    D --> E[10 Corridors]
    E --> F[Learning Data]
    F --> G[100 Receivers]
    G --> H[100 Corridors]
    H --> I[Rich Routing Intelligence]
    I --> J[1000 Receivers]
    J --> K[Marketplace Effect]
```

## Graph Statistics

The graph grows with every new receiver:

| Receivers | Providers | Corridors | Routing Intelligence |
|-----------|-----------|-----------|---------------------|
| 1 | 3 | 3 | Minimal |
| 10 | 3 | 30 | Learning |
| 100 | 3 | 300 | Rich |
| 1000 | 3 | 3000 | Marketplace |

## Future: Payment Graph Network

As more merchants and receivers join, the graph becomes more valuable. The flywheel:

1. More receivers → more corridors
2. More corridors → more payment data
3. More data → better routing decisions
4. Better decisions → lower costs
5. Lower costs → more receivers join

**This is the network effect that makes the payment graph defensible.**
