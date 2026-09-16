"""Tests for routing module."""

from unipay_router.models import (
    Currency,
    PaymentIntent,
    PaymentMethod,
    ReceiverPreferences,
    SenderProfile,
)
from unipay_router.providers import ProviderRegistry
from unipay_router.routing import RoutingEngine


class TestRoutingEngine:
    def setup_method(self):
        self.registry = ProviderRegistry()
        self.engine = RoutingEngine(self.registry)

    def test_find_routes_returns_list(self):
        intent = PaymentIntent(
            amount=10000,
            currency=Currency.INR,
            sender=SenderProfile(
                sender_id="test",
                available_methods=[PaymentMethod.UPI, PaymentMethod.VISA],
            ),
        )
        routes = self.engine.find_routes(intent)
        assert isinstance(routes, list)
        assert len(routes) > 0

    def test_routes_sorted_by_score(self):
        intent = PaymentIntent(
            amount=10000,
            currency=Currency.INR,
            sender=SenderProfile(
                sender_id="test",
                available_methods=[PaymentMethod.UPI, PaymentMethod.VISA],
            ),
        )
        routes = self.engine.find_routes(intent)
        scores = [r.score() for r in routes if r.score() < float("inf")]
        assert scores == sorted(scores)

    def test_max_results(self):
        intent = PaymentIntent(
            amount=10000,
            currency=Currency.INR,
            sender=SenderProfile(
                sender_id="test",
                available_methods=[PaymentMethod.UPI, PaymentMethod.VISA],
            ),
        )
        routes = self.engine.find_routes(intent, max_results=2)
        assert len(routes) <= 2

    def test_receiver_settlement_methods_respected(self):
        """Receiver's rejected settlement methods should not appear in routes."""
        prefs = ReceiverPreferences(
            receiver_id="test",
            preferred_methods=[PaymentMethod.UPI],
            rejected_methods=[PaymentMethod.WALLET],
        )
        intent = PaymentIntent(
            amount=10000,
            currency=Currency.INR,
            sender=SenderProfile(
                sender_id="test",
                available_methods=[PaymentMethod.UPI],
            ),
            receiver=prefs,
        )
        routes = self.engine.find_routes(intent)
        for route in routes:
            if route.score() < float("inf"):
                # Receiver only accepts UPI settlement, not wallet
                assert route.settlement_method == PaymentMethod.UPI

    def test_fee_constraint_applied(self):
        """Routes exceeding receiver's max fee should be excluded."""
        prefs = ReceiverPreferences(
            receiver_id="test",
            preferred_methods=[PaymentMethod.UPI],
            max_fee_absolute=5.0,  # Very low max fee
        )
        intent = PaymentIntent(
            amount=10000,
            currency=Currency.INR,
            sender=SenderProfile(
                sender_id="test",
                available_methods=[PaymentMethod.UPI],
            ),
            receiver=prefs,
        )
        routes = self.engine.find_routes(intent)
        for route in routes:
            if route.score() < float("inf"):
                assert route.fee <= 5.0
