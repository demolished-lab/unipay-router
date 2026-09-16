# Architecture

## System Overview

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Web App]
        MOB[Mobile App]
        API_CLIENT[API Client]
    end

    subgraph "UniPay Router Layer"
        REST[REST API]
        ROUTING[Routing Engine]
        RECEIVER[Receiver Preferences]
        GRAPH[Payment Graph]
        FX[FX Engine]
        WEBHOOK[Webhook Handler]
        RECONCILE[Reconciliation]
    end

    subgraph "Hyperswitch Layer"
        HS[Hyperswitch Server]
        EUCLID[Euclid DSL]
        CONSTRAINT[Constraint Graph]
        DYNAMIC[Dynamic Routing]
        VAULT[Card Vault]
    end

    subgraph "Provider Layer"
        RAZORPAY[Razorpay]
        CASHFREE[Cashfree]
        PAYU[PayU]
    end

    subgraph "External Systems"
        UPI[NPCI UPI]
        VISA[Visa]
        MC[Mastercard]
        RUPAY[RuPay]
        BANK[Bank Networks]
        FX_API[FX Rate APIs]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL)]
        RD[(Redis)]
    end

    WEB --> REST
    MOB --> REST
    API_CLIENT --> REST
    REST --> ROUTING
    REST --> RECEIVER
    ROUTING --> HS
    ROUTING --> GRAPH
    ROUTING --> FX
    HS --> EUCLID --> CONSTRAINT
    EUCLID --> DYNAMIC
    CONSTRAINT --> RAZORPAY
    CONSTRAINT --> CASHFREE
    CONSTRAINT --> PAYU
    RAZORPAY --> UPI
    RAZORPAY --> VISA
    RAZORPAY --> MC
    CASHFREE --> UPI
    CASHFREE --> BANK
    PAYU --> UPI
    PAYU --> RUPAY
    WEBHOOK --> RAZORPAY
    WEBHOOK --> CASHFREE
    WEBHOOK --> PAYU
    FX --> FX_API
    HS --> PG
    HS --> RD
    RECONCILE --> PG
```

## Data Flow

### Payment Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant R as UniPay Router
    participant H as Hyperswitch
    participant P as Provider
    participant B as Bank/UPI

    C->>R: POST /v1/payment-intents
    R->>R: Resolve receiver handle
    R->>R: Get receiver preferences
    R->>H: Find available routes
    H->>H: Apply Euclid DSL rules
    H->>H: Evaluate constraint graph
    H-->>R: Ranked route list
    R->>R: Filter by receiver preferences
    R->>R: Score routes (C+L+F+X+Q)
    R-->>C: Best route + alternatives

    C->>R: POST /confirm
    R->>H: Create payment intent
    H->>P: Route to selected provider
    P->>B: Initiate payment
    B-->>P: Payment result
    P-->>H: Webhook (payment.captured)
    H-->>R: Forward webhook
    R->>R: Update reconciliation
    R-->>C: Payment confirmed
```

### Webhook Flow

```mermaid
sequenceDiagram
    participant P as Provider
    participant H as Hyperswitch
    participant R as UniPay Router
    participant DB as Database

    P->>H: POST /webhooks/{connector}
    H->>H: Verify signature
    H->>H: Parse event
    H->>DB: Update payment status
    H->>R: Forward webhook event
    R->>R: Update reconciliation
    R->>R: Check for discrepancies
    R->>DB: Store reconciliation record
```

## Database Schema

```mermaid
erDiagram
    PAYMENT_INTENTS {
        uuid id PK
        decimal amount
        varchar currency
        varchar sender_id
        varchar receiver_handle
        varchar state
        jsonb selected_route
        timestamp created_at
    }

    RECEIVER_PREFERENCES {
        varchar receiver_id PK
        varchar handle UK
        varchar country
        varchar currency
        jsonb preferred_methods
        jsonb rejected_methods
        decimal max_fee_percentage
        decimal max_fee_absolute
        varchar settlement_speed
    }

    PAYMENT_GRAPH_NODES {
        varchar id PK
        varchar node_type
        varchar label
        jsonb metadata
    }

    PAYMENT_GRAPH_EDGES {
        varchar source FK
        varchar target FK
        varchar edge_type
        float weight
        jsonb metadata
    }

    RECONCILIATION_RECORDS {
        varchar id PK
        uuid payment_intent_id FK
        varchar provider
        varchar provider_payment_id
        int amount
        varchar currency
        varchar provider_status
        varchar our_status
        timestamp last_synced_at
        varchar discrepancy
    }

    PROVIDER_STATS {
        varchar provider PK
        varchar payment_method
        float success_rate
        float avg_latency_ms
        int total_attempts
        int successful_attempts
    }

    PAYMENT_INTENTS ||--o{ RECONCILIATION_RECORDS : has
    PAYMENT_GRAPH_NODES ||--o{ PAYMENT_GRAPH_EDGES : source
    PAYMENT_GRAPH_NODES ||--o{ PAYMENT_GRAPH_EDGES : target
```

## Component Descriptions

### Routing Engine
The core decision-maker. Uses Hyperswitch's Euclid DSL for constraint-based routing, extended with our receiver preference filtering and scoring function.

### Receiver Preferences
The novel layer. Stores how each receiver wants to get paid (methods, fees, speed, currency) and filters routes accordingly.

### Payment Graph
A graph model where nodes are providers, rails, countries, currencies, receivers, and merchants. Edges represent "money can move from A to B under these conditions." Grows with every receiver added.

### FX Engine
Fetches live exchange rates from free APIs (exchangerate-api.com, CurrencyScoop) with caching and fallback to hardcoded rates.

### Webhook Handler
Normalizes incoming webhooks from Razorpay, Cashfree, and PayU into a unified event format. Handles signature verification.

### Reconciliation Engine
Tracks transaction states across all providers, identifies discrepancies, and provides a unified view. This is the "boring" moat that becomes valuable at scale.

## Scalability

```mermaid
graph LR
    subgraph "Phase 1: Prototype"
        P1[Hyperswitch + Router]
        P1 --> P1DB[(SQLite)]
    end

    subgraph "Phase 2: Scale"
        P2[Hyperswitch Cluster]
        P2 --> P2DB[(PostgreSQL)]
        P2 --> P2RD[(Redis Cluster)]
    end

    subgraph "Phase 3: Enterprise"
        P3[Hyperswitch + Router x N]
        P3 --> P3DB[(PostgreSQL HA)]
        P3 --> P3RD[(Redis Cluster)]
        P3 --> P3KH[(Kafka)]
        P3 --> P3CH[(ClickHouse)]
    end
```
