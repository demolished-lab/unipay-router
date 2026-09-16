"""Core data models for the Universal Payment Router."""

from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field

# ── Enums ──────────────────────────────────────────────────────────────────────

class PaymentMethod(str, enum.Enum):
    UPI = "upi"
    VISA = "visa"
    MASTERCARD = "mastercard"
    RUPAY = "rupay"
    NET_BANKING = "net_banking"
    BANK_TRANSFER = "bank_transfer"
    WALLET = "wallet"
    PAYPAL = "paypal"
    CRYPTO = "crypto"


class Currency(str, enum.Enum):
    INR = "INR"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    SGD = "SGD"
    AED = "AED"
    NPR = "NPR"
    BDT = "BDT"
    LKR = "LKR"


class RouteStatus(str, enum.Enum):
    CALCULATED = "calculated"
    ATTEMPTING = "attempting"
    PROCESSING = "processing"
    SETTLED = "settled"
    FAILED = "failed"
    RECOVERING = "recovering"


class TransactionState(str, enum.Enum):
    CREATED = "created"
    INTENT_VALIDATED = "intent_validated"
    ROUTE_SELECTED = "route_selected"
    PAYMENT_INITIATED = "payment_initiated"
    PAYMENT_PROCESSING = "payment_processing"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    SETTLEMENT_PENDING = "settlement_pending"
    SETTLED = "settled"
    REFUND_PENDING = "refund_pending"
    REFUNDED = "refunded"
    RECOVERY_ATTEMPTED = "recovery_attempted"


class SettlementSpeed(str, enum.Enum):
    INSTANT = "instant"
    REAL_TIME = "real_time"
    T_PLUS_1 = "t+1"
    T_PLUS_2 = "t+2"
    T_PLUS_3 = "t+3"
    WEEKLY = "weekly"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ── Core Entities ──────────────────────────────────────────────────────────────

@dataclass
class PaymentMethodConfig:
    method: PaymentMethod
    supported_currencies: list[Currency] = field(default_factory=list)
    settlement_speed: SettlementSpeed = SettlementSpeed.T_PLUS_1
    fixed_fee: float = 0.0
    percentage_fee: float = 0.0
    min_amount: float = 0.0
    max_amount: float = float("inf")
    success_rate: float = 0.95
    enabled: bool = True


@dataclass
class Provider:
    """A payment provider (e.g., Razorpay, PayU, Cashfree)."""
    id: str
    name: str
    supported_methods: list[PaymentMethod] = field(default_factory=list)
    supported_currencies: list[Currency] = field(default_factory=list)
    method_configs: dict[PaymentMethod, PaymentMethodConfig] = field(default_factory=dict)
    settlement_speed: SettlementSpeed = SettlementSpeed.T_PLUS_1
    api_latency_ms: float = 200.0
    is_active: bool = True

    def supports_method(self, method: PaymentMethod) -> bool:
        return method in self.supported_methods and self.method_configs.get(method, PaymentMethodConfig(method=method)).enabled

    def supports_currency(self, currency: Currency) -> bool:
        return currency in self.supported_currencies

    def get_fee(self, method: PaymentMethod, amount: float) -> float:
        config = self.method_configs.get(method, PaymentMethodConfig(method=method))
        return config.fixed_fee + (amount * config.percentage_fee)

    def get_success_rate(self, method: PaymentMethod) -> float:
        config = self.method_configs.get(method, PaymentMethodConfig(method=method))
        return config.success_rate


@dataclass
class ReceiverPreferences:
    """How the receiver wants to get paid."""
    receiver_id: str
    country: str = "IN"
    currency: Currency = Currency.INR
    preferred_methods: list[PaymentMethod] = field(default_factory=lambda: [PaymentMethod.UPI, PaymentMethod.BANK_TRANSFER])
    rejected_methods: list[PaymentMethod] = field(default_factory=list)
    max_fee_percentage: float = 1.0
    max_fee_absolute: float = 100.0
    min_settlement_speed: SettlementSpeed = SettlementSpeed.T_PLUS_1
    settlement_speed_preference: SettlementSpeed = SettlementSpeed.INSTANT

    def accepts_method(self, method: PaymentMethod) -> bool:
        if method in self.rejected_methods:
            return False
        return method in self.preferred_methods

    def accepts_fee(self, fee: float, amount: float) -> bool:
        if amount <= 0:
            return False
        pct = (fee / amount) * 100
        return pct <= self.max_fee_percentage and fee <= self.max_fee_absolute


@dataclass
class SenderProfile:
    """How the sender wants to pay."""
    sender_id: str
    country: str = "IN"
    currency: Currency = Currency.INR
    available_methods: list[PaymentMethod] = field(default_factory=lambda: [PaymentMethod.UPI])
    preferred_method: PaymentMethod | None = None
    max_fee_percentage: float = 2.0
    max_fee_absolute: float = 500.0


@dataclass
class RouteCandidate:
    """A possible route from sender to receiver."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    payer_method: PaymentMethod = PaymentMethod.UPI
    settlement_method: PaymentMethod = PaymentMethod.UPI
    provider: Provider | None = None
    currency: Currency = Currency.INR
    amount: float = 0.0
    fee: float = 0.0
    fx_rate: float = 1.0
    fx_cost: float = 0.0
    total_cost: float = 0.0
    net_received: float = 0.0
    success_probability: float = 0.95
    latency_ms: float = 200.0
    settlement_speed: SettlementSpeed = SettlementSpeed.INSTANT
    risk_score: float = 0.0
    compliance_ok: bool = True
    receiver_accepts: bool = True

    def score(self) -> float:
        """Lower is better. The routing optimization function.

        R* = argmin_R (C_R + L_R + F_R + X_R + Q_R)

        C = cost (fee + fx_cost normalized)
        L = latency (normalized to 0-1)
        F = failure risk (1 - success_probability)
        X = fx cost (already in total_cost)
        Q = compliance/risk penalty
        """
        if not self.compliance_ok or not self.receiver_accepts:
            return float("inf")

        cost_norm = (self.total_cost / self.amount) if self.amount > 0 else 1.0
        latency_norm = min(self.latency_ms / 5000.0, 1.0)
        failure_risk = 1.0 - self.success_probability
        risk_penalty = self.risk_score

        # Weighted sum — lower is better
        return (
            0.35 * cost_norm
            + 0.15 * latency_norm
            + 0.25 * failure_risk
            + 0.15 * (self.fx_cost / self.amount if self.amount > 0 else 0)
            + 0.10 * risk_penalty
        )


@dataclass
class PaymentIntent:
    """A request to route a payment from sender to receiver."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    amount: float = 0.0
    currency: Currency = Currency.INR
    sender: SenderProfile | None = None
    receiver: ReceiverPreferences | None = None
    created_at: float = field(default_factory=time.time)
    routes: list[RouteCandidate] = field(default_factory=list)
    selected_route: RouteCandidate | None = None
    state: TransactionState = TransactionState.CREATED

    @property
    def sender_methods(self) -> list[PaymentMethod]:
        if self.sender:
            return self.sender.available_methods
        return list(PaymentMethod)

    @property
    def receiver_methods(self) -> list[PaymentMethod]:
        if self.receiver:
            return self.receiver.preferred_methods
        return list(PaymentMethod)


@dataclass
class Transaction:
    """An executed payment transaction."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    intent_id: str = ""
    route: RouteCandidate | None = None
    state: TransactionState = TransactionState.CREATED
    state_history: list[tuple[TransactionState, float]] = field(default_factory=list)
    attempts: int = 0
    max_attempts: int = 3
    recovery_routes: list[RouteCandidate] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    settled_at: float | None = None
    error: str | None = None

    def transition(self, new_state: TransactionState, error: str | None = None) -> bool:
        valid_transitions = {
            TransactionState.CREATED: [TransactionState.INTENT_VALIDATED],
            TransactionState.INTENT_VALIDATED: [TransactionState.ROUTE_SELECTED],
            TransactionState.ROUTE_SELECTED: [TransactionState.PAYMENT_INITIATED],
            TransactionState.PAYMENT_INITIATED: [TransactionState.PAYMENT_PROCESSING, TransactionState.PAYMENT_FAILED],
            TransactionState.PAYMENT_PROCESSING: [TransactionState.PAYMENT_SUCCESS, TransactionState.PAYMENT_FAILED],
            TransactionState.PAYMENT_SUCCESS: [TransactionState.SETTLEMENT_PENDING],
            TransactionState.PAYMENT_FAILED: [TransactionState.RECOVERY_ATTEMPTED, TransactionState.SETTLEMENT_PENDING],
            TransactionState.RECOVERY_ATTEMPTED: [TransactionState.PAYMENT_INITIATED, TransactionState.SETTLEMENT_PENDING],
            TransactionState.SETTLEMENT_PENDING: [TransactionState.SETTLED],
            TransactionState.SETTLED: [TransactionState.REFUND_PENDING],
            TransactionState.REFUND_PENDING: [TransactionState.REFUNDED],
        }
        allowed = valid_transitions.get(self.state, [])
        if new_state not in allowed:
            return False
        self.state = new_state
        self.state_history.append((new_state, time.time()))
        self.updated_at = time.time()
        if error:
            self.error = error
        if new_state == TransactionState.SETTLED:
            self.settled_at = time.time()
        return True
