"""REST API — FastAPI/Flask wrapper for the Universal Payment Router.

Endpoints:
  POST /v1/payment-intents       Create payment intent + find route
  GET  /v1/payment-intents/{id}  Get payment status
  POST /v1/receiver-preferences  Set receiver preferences
  GET  /v1/resolve/{handle}     Resolve receiver handle
  GET  /v1/routes               List available routes
  POST /v1/webhooks/{provider}  Handle provider webhooks
  GET  /v1/graph/stats          Payment graph statistics
  GET  /health                  Health check
"""

from __future__ import annotations

import uuid

try:
    from .fx_engine import FXEngine
    from .models import (
        Currency,
        PaymentIntent,
        PaymentMethod,
        ReceiverPreferences,
        SenderProfile,
        SettlementSpeed,
    )
    from .payment_graph import PaymentGraph
    from .providers import ProviderRegistry
    from .receiver_preferences import ReceiverPreferenceEngine
    from .reconciliation import ReconciliationEngine
    from .routing import RoutingEngine
    from .webhook_handler import WebhookHandler
except ImportError:
    from fx_engine import FXEngine
    from models import (
        Currency,
        PaymentIntent,
        PaymentMethod,
        ReceiverPreferences,
        SenderProfile,
        SettlementSpeed,
    )
    from payment_graph import PaymentGraph
    from providers import ProviderRegistry
    from receiver_preferences import ReceiverPreferenceEngine
    from reconciliation import ReconciliationEngine
    from routing import RoutingEngine
    from webhook_handler import WebhookHandler


class UniPayAPI:
    """Unified API for the Universal Payment Router."""

    def __init__(self) -> None:
        self.registry = ProviderRegistry()
        self.routing_engine = RoutingEngine(self.registry)
        self.receiver_engine = ReceiverPreferenceEngine()
        self.payment_graph = PaymentGraph(self.registry)
        self.fx_engine = FXEngine()
        self.webhook_handler = WebhookHandler()
        self.reconciliation = ReconciliationEngine()
        self._payment_intents: dict[str, PaymentIntent] = {}

    # ── Payment Intents ──────────────────────────────────────────────────────

    def create_payment_intent(self, request: dict) -> dict:
        """Create a payment intent and find optimal routes."""
        amount = request.get("amount", 0)
        currency_str = request.get("currency", "INR")
        receiver_handle = request.get("receiver_handle", "")
        sender_data = request.get("sender", {})

        try:
            currency = Currency(currency_str)
        except ValueError:
            return {"error": f"Invalid currency: {currency_str}"}

        # Resolve receiver
        receiver_prefs = self.receiver_engine.resolve_handle(receiver_handle)
        if not receiver_prefs:
            return {"error": f"Receiver not found: {receiver_handle}"}

        # Build sender profile
        sender_methods = []
        for m in sender_data.get("preferred_methods", ["upi"]):
            try:
                sender_methods.append(PaymentMethod(m))
            except ValueError:
                pass
        if not sender_methods:
            sender_methods = [PaymentMethod.UPI]

        sender = SenderProfile(
            sender_id="api_user",
            country=sender_data.get("country", "IN"),
            currency=currency,
            available_methods=sender_methods,
        )

        # Create payment intent
        intent = PaymentIntent(
            id=str(uuid.uuid4()),
            amount=amount,
            currency=currency,
            sender=sender,
            receiver=receiver_prefs,
        )

        # Find routes
        routes = self.routing_engine.find_routes(intent, max_results=5)

        # Filter by receiver preferences
        if receiver_prefs:
            routes = self.receiver_engine.filter_routes(routes, receiver_prefs.receiver_id)

        if not routes:
            return {"error": "No available routes for this combination"}

        intent.routes = routes
        intent.selected_route = routes[0]
        intent.state = intent.state  # Keep current state
        self._payment_intents[intent.id] = intent

        return {
            "id": intent.id,
            "amount": amount,
            "currency": currency_str,
            "route": self._route_to_dict(routes[0]),
            "alternatives": [self._route_to_dict(r) for r in routes[1:]],
        }

    def get_payment_intent(self, payment_id: str) -> dict:
        """Get payment intent details."""
        intent = self._payment_intents.get(payment_id)
        if not intent:
            return {"error": "Payment intent not found"}
        return {
            "id": intent.id,
            "amount": intent.amount,
            "currency": intent.currency.value,
            "state": intent.state.value,
            "selected_route": self._route_to_dict(intent.selected_route) if intent.selected_route else None,
        }

    # ── Receiver Preferences ─────────────────────────────────────────────────

    def create_receiver_preference(self, request: dict) -> dict:
        """Create or update receiver preferences."""
        receiver_id = request.get("receiver_id", "")
        handle = request.get("handle", f"{receiver_id}@unipay")
        country = request.get("country", "IN")
        currency_str = request.get("currency", "INR")

        preferred = []
        for m in request.get("preferred_methods", ["upi"]):
            try:
                preferred.append(PaymentMethod(m))
            except ValueError:
                pass

        rejected = []
        for m in request.get("rejected_methods", []):
            try:
                rejected.append(PaymentMethod(m))
            except ValueError:
                pass

        try:
            currency = Currency(currency_str)
        except ValueError:
            return {"error": f"Invalid currency: {currency_str}"}

        try:
            speed = SettlementSpeed(request.get("settlement_speed", "instant"))
        except ValueError:
            speed = SettlementSpeed.INSTANT

        prefs = ReceiverPreferences(
            receiver_id=receiver_id,
            country=country,
            currency=currency,
            preferred_methods=preferred,
            rejected_methods=rejected,
            max_fee_percentage=request.get("max_fee_percentage", 1.0),
            max_fee_absolute=request.get("max_fee_absolute", 100.0),
            settlement_speed_preference=speed,
        )

        actual_handle = self.receiver_engine.register_receiver(prefs, handle)
        return {"handle": actual_handle, "receiver_id": receiver_id}

    def resolve_handle(self, handle: str) -> dict:
        """Resolve a @handle to receiver preferences."""
        prefs = self.receiver_engine.resolve_handle(handle)
        if not prefs:
            return {"error": f"Handle not found: {handle}"}
        return self.receiver_engine.to_dict(prefs.receiver_id) or {}

    # ── Routes ───────────────────────────────────────────────────────────────

    def list_routes(self, request: dict) -> dict:
        """List available routes for given parameters."""
        amount = request.get("amount", 0)
        currency_str = request.get("currency", "INR")
        receiver_handle = request.get("receiver_handle", "")

        try:
            currency = Currency(currency_str)
        except ValueError:
            return {"error": f"Invalid currency: {currency_str}"}

        receiver_prefs = self.receiver_engine.resolve_handle(receiver_handle) if receiver_handle else None

        intent = PaymentIntent(
            amount=amount,
            currency=currency,
            sender=SenderProfile(
                sender_id="api_user",
                available_methods=[PaymentMethod.UPI, PaymentMethod.VISA, PaymentMethod.MASTERCARD],
            ),
            receiver=receiver_prefs,
        )

        routes = self.routing_engine.find_routes(intent, max_results=10)
        if receiver_prefs:
            routes = self.receiver_engine.filter_routes(routes, receiver_prefs.receiver_id)

        return {
            "routes": [self._route_to_dict(r) for r in routes],
            "count": len(routes),
        }

    # ── FX ───────────────────────────────────────────────────────────────────

    def get_fx_rate(self, from_currency: str, to_currency: str) -> dict:
        """Get exchange rate between two currencies."""
        rate_info = self.fx_engine.get_rate(from_currency, to_currency)
        return {
            "from": from_currency,
            "to": to_currency,
            "rate": rate_info.rate,
            "spread": rate_info.spread,
            "source": rate_info.source,
        }

    # ── Webhooks ─────────────────────────────────────────────────────────────

    def handle_webhook(self, provider: str, payload: bytes, headers: dict[str, str]) -> dict:
        """Process an incoming webhook from a payment provider."""
        event = self.webhook_handler.process(provider, payload, headers)
        if not event:
            return {"error": "Invalid webhook or unknown provider"}

        return {
            "event": event.event.value,
            "payment_id": event.payment_id,
            "provider": event.provider,
            "status": event.status,
        }

    # ── Graph ────────────────────────────────────────────────────────────────

    def get_graph_stats(self) -> dict:
        """Get payment graph statistics."""
        return self.payment_graph.stats()

    # ── Health ───────────────────────────────────────────────────────────────

    def health_check(self) -> dict:
        """System health check."""
        return {
            "status": "ok",
            "providers": len(self.registry.all()),
            "receivers": len(self.receiver_engine.list_receivers()),
            "payment_intents": len(self._payment_intents),
            "graph_nodes": self.payment_graph.node_count(),
            "graph_edges": self.payment_graph.edge_count(),
        }

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _route_to_dict(self, route) -> dict:
        return {
            "payer_method": route.payer_method.value,
            "settlement_method": route.settlement_method.value,
            "provider": route.provider.name if route.provider else "N/A",
            "amount": route.amount,
            "currency": route.currency.value,
            "fee": route.fee,
            "fx_cost": route.fx_cost,
            "net_received": route.net_received,
            "success_probability": route.success_probability,
            "settlement_speed": route.settlement_speed.value,
            "score": route.score(),
        }
