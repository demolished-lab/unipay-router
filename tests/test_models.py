"""Tests for models module."""

from unipay_router.models import (
    Currency,
    PaymentMethod,
    ReceiverPreferences,
    RouteCandidate,
    Transaction,
    TransactionState,
)


class TestPaymentMethod:
    def test_enum_values(self):
        assert PaymentMethod.UPI.value == "upi"
        assert PaymentMethod.VISA.value == "visa"
        assert PaymentMethod.MASTERCARD.value == "mastercard"

    def test_from_value(self):
        assert PaymentMethod("upi") == PaymentMethod.UPI
        assert PaymentMethod("visa") == PaymentMethod.VISA


class TestCurrency:
    def test_enum_values(self):
        assert Currency.INR.value == "INR"
        assert Currency.USD.value == "USD"


class TestRouteCandidate:
    def test_score_compliance_fail(self):
        route = RouteCandidate(compliance_ok=False)
        assert route.score() == float("inf")

    def test_receiver_rejects(self):
        route = RouteCandidate(receiver_accepts=False)
        assert route.score() == float("inf")

    def test_score_low_cost(self):
        route = RouteCandidate(
            amount=1000,
            fee=10,
            fx_cost=0,
            total_cost=10,
            latency_ms=100,
            success_probability=0.99,
            risk_score=0.1,
        )
        score = route.score()
        assert 0 <= score < 1

    def test_score_high_cost(self):
        low_cost = RouteCandidate(
            amount=1000, fee=10, fx_cost=0, total_cost=10, latency_ms=100, success_probability=0.99
        )
        high_cost = RouteCandidate(
            amount=1000, fee=100, fx_cost=0, total_cost=100, latency_ms=100, success_probability=0.99
        )
        assert low_cost.score() < high_cost.score()


class TestTransaction:
    def test_valid_transition(self):
        txn = Transaction(state=TransactionState.CREATED)
        assert txn.transition(TransactionState.INTENT_VALIDATED)
        assert txn.state == TransactionState.INTENT_VALIDATED

    def test_invalid_transition(self):
        txn = Transaction(state=TransactionState.CREATED)
        assert not txn.transition(TransactionState.SETTLED)
        assert txn.state == TransactionState.CREATED

    def test_full_lifecycle(self):
        txn = Transaction(state=TransactionState.CREATED)
        transitions = [
            TransactionState.INTENT_VALIDATED,
            TransactionState.ROUTE_SELECTED,
            TransactionState.PAYMENT_INITIATED,
            TransactionState.PAYMENT_PROCESSING,
            TransactionState.PAYMENT_SUCCESS,
            TransactionState.SETTLEMENT_PENDING,
            TransactionState.SETTLED,
        ]
        for state in transitions:
            assert txn.transition(state), f"Failed to transition to {state}"
        assert txn.state == TransactionState.SETTLED
        assert txn.settled_at is not None


class TestReceiverPreferences:
    def test_accepts_method(self):
        prefs = ReceiverPreferences(
            receiver_id="test",
            preferred_methods=[PaymentMethod.UPI, PaymentMethod.VISA],
        )
        assert prefs.accepts_method(PaymentMethod.UPI)
        assert prefs.accepts_method(PaymentMethod.VISA)
        assert not prefs.accepts_method(PaymentMethod.MASTERCARD)

    def test_rejects_method(self):
        prefs = ReceiverPreferences(
            receiver_id="test",
            preferred_methods=[PaymentMethod.UPI],
            rejected_methods=[PaymentMethod.WALLET],
        )
        assert prefs.accepts_method(PaymentMethod.UPI)
        assert not prefs.accepts_method(PaymentMethod.WALLET)

    def test_accepts_fee(self):
        prefs = ReceiverPreferences(
            receiver_id="test",
            max_fee_percentage=1.0,
            max_fee_absolute=100.0,
        )
        assert prefs.accepts_fee(10, 10000)  # 0.1% - OK
        assert not prefs.accepts_fee(200, 10000)  # 2% - too high percentage
        assert not prefs.accepts_fee(150, 10000)  # > max_absolute
