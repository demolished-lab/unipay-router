"""Receiver Preference Engine — the novel layer that lets receivers define how they get paid.

This is the key differentiator: instead of only asking "how do you want to pay?",
we also ask "how do you want to receive?"
"""

from __future__ import annotations

from .models import (
    Currency,
    PaymentMethod,
    ReceiverPreferences,
    RouteCandidate,
    SettlementSpeed,
)


class ReceiverPreferenceEngine:
    """Manages receiver preferences and filters routes accordingly.

    In production, preferences would be stored in a database.
    This in-memory implementation demonstrates the concept.
    """

    def __init__(self) -> None:
        self._preferences: dict[str, ReceiverPreferences] = {}
        self._handles: dict[str, str] = {}  # handle -> receiver_id
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Load some demo receiver preferences."""
        receivers = [
            ReceiverPreferences(
                receiver_id="bob",
                country="IN",
                currency=Currency.INR,
                preferred_methods=[PaymentMethod.UPI, PaymentMethod.BANK_TRANSFER],
                rejected_methods=[PaymentMethod.WALLET],
                max_fee_percentage=0.5,
                max_fee_absolute=50.0,
                settlement_speed_preference=SettlementSpeed.INSTANT,
            ),
            ReceiverPreferences(
                receiver_id="alice_sg",
                country="SG",
                currency=Currency.SGD,
                preferred_methods=[PaymentMethod.VISA, PaymentMethod.PAYPAL],
                max_fee_percentage=3.0,
                settlement_speed_preference=SettlementSpeed.T_PLUS_1,
            ),
            ReceiverPreferences(
                receiver_id="shop_india",
                country="IN",
                currency=Currency.INR,
                preferred_methods=[PaymentMethod.UPI, PaymentMethod.VISA, PaymentMethod.MASTERCARD],
                max_fee_percentage=2.0,
                settlement_speed_preference=SettlementSpeed.T_PLUS_1,
            ),
        ]
        for recv in receivers:
            self._preferences[recv.receiver_id] = recv
            self._handles[recv.receiver_id] = recv.receiver_id

    def register_receiver(self, receiver: ReceiverPreferences, handle: str | None = None) -> str:
        """Register a receiver with preferences. Returns handle."""
        self._preferences[receiver.receiver_id] = receiver
        h = handle or f"{receiver.receiver_id}@unipay"
        self._handles[h] = receiver.receiver_id
        return h

    def resolve_handle(self, handle: str) -> ReceiverPreferences | None:
        """Resolve a @handle to receiver preferences (like DNS for payments)."""
        receiver_id = self._handles.get(handle)
        if receiver_id:
            return self._preferences.get(receiver_id)
        # Try direct receiver_id lookup
        return self._preferences.get(handle)

    def get_receiver(self, receiver_id: str) -> ReceiverPreferences | None:
        return self._preferences.get(receiver_id)

    def list_receivers(self) -> list[ReceiverPreferences]:
        return list(self._preferences.values())

    def filter_routes(
        self,
        routes: list[RouteCandidate],
        receiver_id: str,
    ) -> list[RouteCandidate]:
        """Filter routes based on receiver preferences."""
        prefs = self._preferences.get(receiver_id)
        if not prefs:
            return routes

        filtered = []
        for route in routes:
            if not self._validate_route(route, prefs):
                continue
            filtered.append(route)
        return filtered

    def _validate_route(self, route: RouteCandidate, prefs: ReceiverPreferences) -> bool:
        """Validate a route against receiver preferences."""
        # Check method acceptance
        if not prefs.accepts_method(route.settlement_method):
            return False

        # Check fee constraint
        if not prefs.accepts_fee(route.fee, route.amount):
            return False

        # Check settlement speed preference
        speed_order = [
            SettlementSpeed.INSTANT,
            SettlementSpeed.REAL_TIME,
            SettlementSpeed.T_PLUS_1,
            SettlementSpeed.T_PLUS_2,
            SettlementSpeed.T_PLUS_3,
            SettlementSpeed.WEEKLY,
        ]
        try:
            settle_idx = speed_order.index(route.settlement_speed)
            pref_idx = speed_order.index(prefs.settlement_speed_preference)
            if settle_idx > pref_idx + 1:
                return False  # Too slow for receiver's preference
        except ValueError:
            pass

        # Check currency compatibility
        if route.currency != prefs.currency:
            # Allow cross-currency but flag it
            pass

        return True

    def get_acceptable_methods(self, receiver_id: str) -> list[PaymentMethod]:
        """Get list of payment methods a receiver accepts."""
        prefs = self._preferences.get(receiver_id)
        if not prefs:
            return list(PaymentMethod)
        return prefs.preferred_methods

    def get_max_fee(self, receiver_id: str) -> tuple[float, float]:
        """Get receiver's max fee (percentage, absolute)."""
        prefs = self._preferences.get(receiver_id)
        if not prefs:
            return (1.0, 100.0)
        return (prefs.max_fee_percentage, prefs.max_fee_absolute)

    def update_preferences(self, receiver_id: str, **kwargs) -> bool:
        """Update receiver preferences."""
        prefs = self._preferences.get(receiver_id)
        if not prefs:
            return False
        for key, value in kwargs.items():
            if hasattr(prefs, key):
                setattr(prefs, key, value)
        return True

    def to_dict(self, receiver_id: str) -> dict | None:
        """Serialize receiver preferences to dict."""
        prefs = self._preferences.get(receiver_id)
        if not prefs:
            return None
        return {
            "receiver_id": prefs.receiver_id,
            "country": prefs.country,
            "currency": prefs.currency.value,
            "preferred_methods": [m.value for m in prefs.preferred_methods],
            "rejected_methods": [m.value for m in prefs.rejected_methods],
            "max_fee_percentage": prefs.max_fee_percentage,
            "max_fee_absolute": prefs.max_fee_absolute,
            "settlement_speed_preference": prefs.settlement_speed_preference.value,
        }
