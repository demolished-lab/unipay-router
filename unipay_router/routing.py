"""Routing engine — the mathematical heart of the Universal Payment Router.

R* = argmin_R (C_R + L_R + F_R + X_R + Q_R)

C = cost (fee normalized)
L = latency (normalized)
F = failure risk (1 - success_probability)
X = FX cost
Q = compliance/risk penalty

Subject to:
  R ∈ legally available routes
  R ∈ technically available routes
  ReceiverPreference(R) = True
"""

from __future__ import annotations

from .models import (
    Currency,
    PaymentIntent,
    PaymentMethod,
    RouteCandidate,
    SettlementSpeed,
)
from .providers import Provider, ProviderRegistry, get_fx_rate


class RoutingEngine:
    """Evaluates all possible routes and returns the optimal one."""

    def __init__(self, registry: ProviderRegistry | None = None) -> None:
        self.registry = registry or ProviderRegistry()
        self._route_history: list[RouteCandidate] = []
        self._success_stats: dict[str, list[bool]] = {}

    def find_routes(
        self,
        intent: PaymentIntent,
        max_results: int = 5,
    ) -> list[RouteCandidate]:
        """Find all valid routes for a payment intent, scored and ranked."""
        candidates: list[RouteCandidate] = []

        sender_methods = set(intent.sender_methods)
        receiver_methods = set(intent.receiver_methods)
        receiver = intent.receiver

        # For each sender method x receiver method x provider combination
        for payer_method in sender_methods:
            for settle_method in receiver_methods:
                if receiver and not receiver.accepts_method(settle_method):
                    continue

                # Find providers that can handle the payer method in sender's currency
                capable_providers = self.registry.find_capable(
                    payer_method, intent.currency
                )

                # For cross-border: also check providers that support both currencies
                if receiver and receiver.currency != intent.currency:
                    # Find providers that support the receiver's currency for settlement
                    settle_providers = self.registry.find_by_currency(receiver.currency)
                    # Merge without duplicates
                    existing_ids = {p.id for p in capable_providers}
                    for sp in settle_providers:
                        if sp.id not in existing_ids:
                            capable_providers.append(sp)

                for provider in capable_providers:
                    candidate = self._evaluate_route(
                        intent=intent,
                        payer_method=payer_method,
                        settle_method=settle_method,
                        provider=provider,
                    )
                    if candidate is not None:
                        candidates.append(candidate)

                # Cross-method: find providers that can bridge payer_method -> settle_method
                # e.g., Visa -> UPI via a provider that accepts both
                if payer_method != settle_method:
                    # Find providers that support the settle method in receiver's currency
                    if receiver:
                        bridge_providers = self.registry.find_capable(
                            settle_method, receiver.currency
                        )
                        for provider in bridge_providers:
                            candidate = self._evaluate_route(
                                intent=intent,
                                payer_method=payer_method,
                                settle_method=settle_method,
                                provider=provider,
                            )
                            if candidate is not None:
                                candidates.append(candidate)

        # Sort by score (lower is better)
        candidates.sort(key=lambda r: r.score())

        # Deduplicate by provider + payer_method + settle_method
        seen = set()
        unique = []
        for c in candidates:
            key = (c.provider.id if c.provider else "", c.payer_method, c.settlement_method)
            if key not in seen:
                seen.add(key)
                unique.append(c)

        # Record for learning
        for c in unique[:max_results]:
            self._route_history.append(c)

        return unique[:max_results]

    def select_best(self, intent: PaymentIntent) -> RouteCandidate | None:
        """Select the single best route for a payment intent."""
        routes = self.find_routes(intent, max_results=1)
        return routes[0] if routes else None

    def _evaluate_route(
        self,
        intent: PaymentIntent,
        payer_method: PaymentMethod,
        settle_method: PaymentMethod,
        provider: Provider,
    ) -> RouteCandidate | None:
        """Evaluate a specific route candidate."""
        amount = intent.amount
        currency = intent.currency
        receiver = intent.receiver

        # Check provider supports the settle method
        if not provider.supports_method(settle_method):
            return None

        # Calculate fee
        fee = provider.get_fee(payer_method, amount)

        # Check receiver fee constraint
        if receiver and not receiver.accepts_fee(fee, amount):
            return None

        # FX cost (if cross-currency)
        fx_rate, fx_spread = 0.0, 0.0
        fx_cost = 0.0
        net_received = amount

        if receiver and receiver.currency != currency:
            fx_rate, fx_spread = get_fx_rate(currency, receiver.currency)
            if fx_rate == 0:
                return None  # No FX path available
            fx_cost = amount * fx_spread
            net_received = (amount - fee - fx_cost) * fx_rate
        else:
            net_received = amount - fee

        # Success probability from provider stats + learning
        base_success = provider.get_success_rate(payer_method)
        learned_success = self._get_learned_success(provider.id, payer_method)
        success_prob = 0.7 * base_success + 0.3 * learned_success if learned_success is not None else base_success

        # Risk score (simplified)
        risk_score = 0.0
        if amount > 100000:
            risk_score += 0.2
        if amount > 500000:
            risk_score += 0.3
        if currency not in (Currency.INR,):
            risk_score += 0.1

        # Compliance check (simplified)
        compliance_ok = True
        if receiver and receiver.country == "IN" and payer_method in (PaymentMethod.CRYPTO,):
            compliance_ok = False  # RBI restrictions

        # Settlement speed
        settle_config = provider.method_configs.get(settle_method)
        settlement_speed = settle_config.settlement_speed if settle_config else provider.settlement_speed

        # Speed preference check
        if receiver:
            speed_order = [
                SettlementSpeed.INSTANT,
                SettlementSpeed.REAL_TIME,
                SettlementSpeed.T_PLUS_1,
                SettlementSpeed.T_PLUS_2,
                SettlementSpeed.T_PLUS_3,
                SettlementSpeed.WEEKLY,
            ]
            try:
                settle_idx = speed_order.index(settlement_speed)
                pref_idx = speed_order.index(receiver.settlement_speed_preference)
                if settle_idx > pref_idx + 1:
                    risk_score += 0.1  # Penalty for slow settlement
            except ValueError:
                pass

        total_cost = fee + fx_cost

        return RouteCandidate(
            payer_method=payer_method,
            settlement_method=settle_method,
            provider=provider,
            currency=currency,
            amount=amount,
            fee=fee,
            fx_rate=fx_rate,
            fx_cost=fx_cost,
            total_cost=total_cost,
            net_received=net_received,
            success_probability=success_prob,
            latency_ms=provider.api_latency_ms,
            settlement_speed=settlement_speed,
            risk_score=risk_score,
            compliance_ok=compliance_ok,
            receiver_accepts=receiver.accepts_method(settle_method) if receiver else True,
        )

    def record_outcome(self, route: RouteCandidate, success: bool) -> None:
        """Record transaction outcome for learning."""
        key = f"{route.provider.id}:{route.payer_method.value}"
        if key not in self._success_stats:
            self._success_stats[key] = []
        self._success_stats[key].append(success)

    def _get_learned_success(self, provider_id: str, method: PaymentMethod) -> float | None:
        key = f"{provider_id}:{method.value}"
        stats = self._success_stats.get(key, [])
        if not stats:
            return None
        return sum(stats) / len(stats)

    def get_recovery_routes(
        self,
        failed_route: RouteCandidate,
        intent: PaymentIntent,
        exclude_providers: list[str] | None = None,
    ) -> list[RouteCandidate]:
        """Find alternative routes after a failure (intelligent retry)."""
        exclude = set(exclude_providers or [])
        exclude.add(failed_route.provider.id if failed_route.provider else "")

        all_routes = self.find_routes(intent, max_results=10)
        recovery = [
            r for r in all_routes
            if r.provider and r.provider.id not in exclude
        ]
        return recovery[:3]
