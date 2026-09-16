"""CLI demo — interactive payment routing harness."""

from __future__ import annotations

import json
import sys
import time

from .graph import PaymentGraph
from .models import (
    Currency,
    PaymentIntent,
    PaymentMethod,
    ReceiverPreferences,
    SenderProfile,
    SettlementSpeed,
    Transaction,
    TransactionState,
)
from .providers import ProviderRegistry
from .routing import RoutingEngine


def _print_header(title: str) -> None:
    w = 60
    print()
    print("=" * w)
    print(f"  {title}")
    print("=" * w)


def _print_route(route, idx: int = 0) -> None:
    print(f"\n  Route #{idx + 1}  (score: {route.score():.4f})")
    print(f"  | Payer method:    {route.payer_method.value}")
    print(f"  | Settlement:      {route.settlement_method.value}")
    print(f"  | Provider:        {route.provider.name if route.provider else 'N/A'}")
    print(f"  | Amount:          {route.currency.value} {route.amount:,.2f}")
    print(f"  | Fee:             {route.currency.value} {route.fee:,.2f}")
    if route.fx_cost > 0:
        print(f"  | FX cost:         {route.currency.value} {route.fx_cost:,.2f}")
        print(f"  | FX rate:         {route.fx_rate:.4f}")
    print(f"  | Net received:    {route.net_received:,.2f}")
    print(f"  | Success prob:    {route.success_probability:.1%}")
    print(f"  | Latency:         {route.latency_ms:.0f}ms")
    print(f"  | Settlement:      {route.settlement_speed.value}")
    print(f"  | Risk score:      {route.risk_score:.2f}")
    print(f"  | Compliance:      {'OK' if route.compliance_ok else 'BLOCKED'}")
    print(f"  | Receiver accepts: {'Yes' if route.receiver_accepts else 'No'}")


def _print_transaction(tx: Transaction) -> None:
    print(f"\n  Transaction {tx.id[:8]}")
    print(f"  | State:      {tx.state.value}")
    print(f"  | Attempts:   {tx.attempts}/{tx.max_attempts}")
    if tx.route:
        print(f"  | Route:      {tx.route.payer_method.value} -> {tx.route.settlement_method.value}")
        print(f"  | Provider:   {tx.route.provider.name if tx.route.provider else 'N/A'}")
    if tx.error:
        print(f"  | Error:      {tx.error}")
    if tx.settled_at:
        elapsed = tx.settled_at - tx.created_at
        print(f"  | Settled in: {elapsed:.2f}s")
    print(f"  | States:     {' -> '.join(s.value for s, _ in tx.state_history)}")


def demo_basic_routing(engine: RoutingEngine) -> None:
    """Demo: basic UPI -> UPI routing."""
    _print_header("DEMO 1: Basic UPI -> UPI Routing")

    intent = PaymentIntent(
        amount=5000,
        currency=Currency.INR,
        sender=SenderProfile(
            sender_id="alice",
            country="IN",
            currency=Currency.INR,
            available_methods=[PaymentMethod.UPI],
        ),
        receiver=ReceiverPreferences(
            receiver_id="bob",
            country="IN",
            currency=Currency.INR,
            preferred_methods=[PaymentMethod.UPI, PaymentMethod.BANK_TRANSFER],
            max_fee_percentage=1.0,
            settlement_speed_preference=SettlementSpeed.INSTANT,
        ),
    )

    routes = engine.find_routes(intent)
    print(f"\n  Found {len(routes)} route(s) for Rs.{intent.amount:,.0f}")
    for i, route in enumerate(routes):
        _print_route(route, i)

    if routes:
        best = routes[0]
        intent.selected_route = best
        print(f"\n  >> Best route: {best.payer_method.value} -> {best.settlement_method.value} via {best.provider.name}")
        print(f"    Fee: Rs.{best.fee:,.2f} | Net: Rs.{best.net_received:,.2f} | Success: {best.success_probability:.1%}")


def demo_cross_method(engine: RoutingEngine) -> None:
    """Demo: Card -> UPI (different sender/receiver methods)."""
    _print_header("DEMO 2: Card -> UPI (Cross-Method)")

    intent = PaymentIntent(
        amount=15000,
        currency=Currency.INR,
        sender=SenderProfile(
            sender_id="alice_intl",
            country="IN",
            currency=Currency.INR,
            available_methods=[PaymentMethod.VISA, PaymentMethod.MASTERCARD],
        ),
        receiver=ReceiverPreferences(
            receiver_id="bob_local",
            country="IN",
            currency=Currency.INR,
            preferred_methods=[PaymentMethod.UPI],
            max_fee_percentage=2.0,
            settlement_speed_preference=SettlementSpeed.T_PLUS_1,
        ),
    )

    routes = engine.find_routes(intent)
    print(f"\n  Found {len(routes)} route(s) for Rs.{intent.amount:,.0f}")
    for i, route in enumerate(routes):
        _print_route(route, i)


def demo_cross_border(engine: RoutingEngine) -> None:
    """Demo: USD -> INR cross-border."""
    _print_header("DEMO 3: Cross-Border (USD -> INR)")

    intent = PaymentIntent(
        amount=100,
        currency=Currency.USD,
        sender=SenderProfile(
            sender_id="alice_us",
            country="US",
            currency=Currency.USD,
            available_methods=[PaymentMethod.VISA, PaymentMethod.MASTERCARD, PaymentMethod.PAYPAL],
        ),
        receiver=ReceiverPreferences(
            receiver_id="bob_in",
            country="IN",
            currency=Currency.INR,
            preferred_methods=[PaymentMethod.BANK_TRANSFER, PaymentMethod.UPI],
            max_fee_percentage=3.0,
            settlement_speed_preference=SettlementSpeed.T_PLUS_2,
        ),
    )

    routes = engine.find_routes(intent)
    print(f"\n  Found {len(routes)} route(s) for ${intent.amount:,.0f} -> INR")
    for i, route in enumerate(routes):
        _print_route(route, i)


def demo_receiver_preferences(engine: RoutingEngine) -> None:
    """Demo: receiver rejects certain methods."""
    _print_header("DEMO 4: Receiver Preference Constraints")

    intent = PaymentIntent(
        amount=8000,
        currency=Currency.INR,
        sender=SenderProfile(
            sender_id="alice_flexible",
            country="IN",
            currency=Currency.INR,
            available_methods=[PaymentMethod.UPI, PaymentMethod.VISA, PaymentMethod.MASTERCARD, PaymentMethod.WALLET],
        ),
            receiver=ReceiverPreferences(
            receiver_id="bob_picky",
            country="IN",
            currency=Currency.INR,
            preferred_methods=[PaymentMethod.UPI, PaymentMethod.BANK_TRANSFER],
            rejected_methods=[PaymentMethod.WALLET],
            max_fee_percentage=0.5,
            max_fee_absolute=50.0,
            settlement_speed_preference=SettlementSpeed.INSTANT,
        ),
    )

    routes = engine.find_routes(intent)
    print(f"\n  Found {len(routes)} route(s) for Rs.{intent.amount:,.0f}")
    print(f"  Receiver rejects: {[m.value for m in intent.receiver.rejected_methods]}")
    print(f"  Receiver prefers: {[m.value for m in intent.receiver.preferred_methods]}")
    for i, route in enumerate(routes):
        _print_route(route, i)


def demo_failure_recovery(engine: RoutingEngine) -> None:
    """Demo: failure recovery with intelligent retry."""
    _print_header("DEMO 5: Failure Recovery")

    intent = PaymentIntent(
        amount=12000,
        currency=Currency.INR,
        sender=SenderProfile(
            sender_id="alice_retry",
            country="IN",
            currency=Currency.INR,
            available_methods=[PaymentMethod.UPI, PaymentMethod.VISA],
        ),
        receiver=ReceiverPreferences(
            receiver_id="bob_retry",
            country="IN",
            currency=Currency.INR,
            preferred_methods=[PaymentMethod.UPI, PaymentMethod.BANK_TRANSFER],
        ),
    )

    routes = engine.find_routes(intent)
    if not routes:
        print("  No routes found.")
        return

    best = routes[0]
    print(f"\n  Attempting route: {best.payer_method.value} via {best.provider.name}")

    # Simulate failure
    print(f"\n  [FAIL] {best.provider.name} returned: timeout")
    engine.record_outcome(best, success=False)

    # Find recovery routes
    recovery = engine.get_recovery_routes(best, intent)
    print(f"\n  Found {len(recovery)} recovery route(s):")
    for i, route in enumerate(recovery):
        _print_route(route, i)

    if recovery:
        print(f"\n  >> Retrying with: {recovery[0].provider.name}")
        engine.record_outcome(recovery[0], success=True)
        print(f"  >> Recovery successful via {recovery[0].provider.name}")


def demo_transaction_lifecycle(engine: RoutingEngine) -> None:
    """Demo: full transaction lifecycle with state machine."""
    _print_header("DEMO 6: Transaction Lifecycle")

    intent = PaymentIntent(
        amount=25000,
        currency=Currency.INR,
        sender=SenderProfile(
            sender_id="alice_lc",
            country="IN",
            currency=Currency.INR,
            available_methods=[PaymentMethod.UPI, PaymentMethod.VISA],
        ),
        receiver=ReceiverPreferences(
            receiver_id="bob_lc",
            country="IN",
            currency=Currency.INR,
            preferred_methods=[PaymentMethod.UPI],
        ),
    )

    route = engine.select_best(intent)
    if not route:
        print("  No route found.")
        return

    tx = Transaction(intent_id=intent.id, route=route)
    print(f"\n  Transaction created: {tx.id[:8]}")

    # Walk through states
    transitions = [
        (TransactionState.INTENT_VALIDATED, None),
        (TransactionState.ROUTE_SELECTED, None),
        (TransactionState.PAYMENT_INITIATED, None),
        (TransactionState.PAYMENT_PROCESSING, None),
        (TransactionState.PAYMENT_SUCCESS, None),
        (TransactionState.SETTLEMENT_PENDING, None),
        (TransactionState.SETTLED, None),
    ]

    for state, error in transitions:
        ok = tx.transition(state, error)
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] -> {state.value}")

    _print_transaction(tx)


def demo_payment_graph(engine: RoutingEngine) -> None:
    """Demo: payment graph showing network structure."""
    _print_header("DEMO 7: Payment Graph")

    graph = PaymentGraph(engine.registry)

    # Add some receivers and merchants
    graph.add_receiver("bob", "IN", [PaymentMethod.UPI, PaymentMethod.BANK_TRANSFER], Currency.INR)
    graph.add_receiver("alice_sg", "SG", [PaymentMethod.VISA, PaymentMethod.PAYPAL], Currency.SGD)
    graph.add_merchant("flipkart", "IN", [PaymentMethod.UPI, PaymentMethod.VISA, PaymentMethod.MASTERCARD], Currency.INR)
    graph.add_merchant("shopify_us", "US", [PaymentMethod.VISA, PaymentMethod.MASTERCARD, PaymentMethod.PAYPAL], Currency.USD)

    stats = graph.stats()
    print("\n  Graph Statistics:")
    print(f"  | Total nodes: {stats['total_nodes']}")
    print(f"  | Total edges: {stats['total_edges']}")
    print(f"  | Node types: {json.dumps(stats['node_types'], indent=4)}")
    print(f"  | Edge types: {json.dumps(stats['edge_types'], indent=4)}")

    # Find a path
    path = graph.find_path("receiver:bob", "provider:paypal_intl")
    if path:
        print("\n  Path from bob -> PayPal:")
        for edge in path:
            print(f"    {edge.source} --[{edge.edge_type}]--> {edge.target}")


def demo_multi_intent_batch(engine: RoutingEngine) -> None:
    """Demo: batch routing for multiple intents."""
    _print_header("DEMO 8: Batch Routing (100 intents)")

    intents = []
    methods = list(PaymentMethod)
    currencies = [Currency.INR, Currency.USD, Currency.EUR]
    amounts = [100, 500, 1000, 5000, 10000, 50000, 100000]

    import random
    random.seed(42)

    for i in range(100):
        amt = random.choice(amounts)
        cur = random.choice(currencies)
        sender_methods = random.sample(methods, k=min(2, len(methods)))
        receiver_methods = random.sample(
            [PaymentMethod.UPI, PaymentMethod.BANK_TRANSFER, PaymentMethod.WALLET],
            k=random.randint(1, 2),
        )
        intents.append(PaymentIntent(
            amount=amt,
            currency=cur,
            sender=SenderProfile(
                sender_id=f"user_{i}",
                country="IN",
                currency=cur,
                available_methods=sender_methods,
            ),
            receiver=ReceiverPreferences(
                receiver_id=f"recv_{i}",
                country="IN",
                currency=Currency.INR,
                preferred_methods=receiver_methods,
            ),
        ))

    start = time.time()
    results = []
    for intent in intents:
        route = engine.select_best(intent)
        results.append((intent, route))
    elapsed = time.time() - start

    found = sum(1 for _, r in results if r is not None)
    avg_score = (
        sum(r.score() for _, r in results if r is not None) / found
        if found > 0
        else 0
    )

    print(f"\n  Processed {len(intents)} intents in {elapsed*1000:.1f}ms")
    print(f"  | Routes found: {found}/{len(intents)}")
    print(f"  | Success rate: {found/len(intents):.1%}")
    print(f"  | Avg score:    {avg_score:.4f}")
    print(f"  | Throughput:   {len(intents)/elapsed:,.0f} intents/sec")


def interactive_mode(engine: RoutingEngine) -> None:
    """Interactive CLI for custom routing queries."""
    _print_header("INTERACTIVE MODE")
    print("  Enter payment details to find optimal routes.")
    print("  Type 'quit' to exit.\n")

    while True:
        try:
            amount_str = input("  Amount: ").strip()
            if amount_str.lower() in ("quit", "exit", "q"):
                break
            amount = float(amount_str)

            currency_str = input("  Currency (INR/USD/EUR/GBP/SGD) [INR]: ").strip().upper() or "INR"
            try:
                currency = Currency(currency_str)
            except ValueError:
                print("  Invalid currency. Using INR.")
                currency = Currency.INR

            print("  Sender methods (comma-separated): upi,visa,mastercard,rupay,net_banking,bank_transfer,wallet,paypal")
            sender_methods_str = input("  [upi]: ").strip() or "upi"
            sender_methods = []
            for m in sender_methods_str.split(","):
                m = m.strip().lower()
                try:
                    sender_methods.append(PaymentMethod(m))
                except ValueError:
                    pass
            if not sender_methods:
                sender_methods = [PaymentMethod.UPI]

            print("  Receiver preferred methods (comma-separated):")
            recv_methods_str = input("  [upi,bank_transfer]: ").strip() or "upi,bank_transfer"
            recv_methods = []
            for m in recv_methods_str.split(","):
                m = m.strip().lower()
                try:
                    recv_methods.append(PaymentMethod(m))
                except ValueError:
                    pass
            if not recv_methods:
                recv_methods = [PaymentMethod.UPI, PaymentMethod.BANK_TRANSFER]

            max_fee_str = input("  Max fee % [1.0]: ").strip() or "1.0"
            max_fee = float(max_fee_str)

            intent = PaymentIntent(
                amount=amount,
                currency=currency,
                sender=SenderProfile(
                    sender_id="interactive_user",
                    country="IN",
                    currency=currency,
                    available_methods=sender_methods,
                ),
                receiver=ReceiverPreferences(
                    receiver_id="interactive_recv",
                    country="IN",
                    currency=Currency.INR,
                    preferred_methods=recv_methods,
                    max_fee_percentage=max_fee,
                ),
            )

            routes = engine.find_routes(intent)
            if not routes:
                print("\n  No valid routes found for this combination.\n")
                continue

            print(f"\n  Found {len(routes)} route(s):")
            for i, route in enumerate(routes):
                _print_route(route, i)

            best = routes[0]
            print(f"\n  >> Best: {best.payer_method.value} -> {best.settlement_method.value} via {best.provider.name}")
            print(f"    Fee: {currency.value} {best.fee:,.2f} | Net: {best.net_received:,.2f} | Success: {best.success_probability:.1%}\n")

        except (ValueError, EOFError):
            print("  Invalid input. Try again.")
        except KeyboardInterrupt:
            break

    print("\n  Goodbye!")


def main() -> None:
    """Main CLI entry point."""
    registry = ProviderRegistry()
    engine = RoutingEngine(registry)

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        demos = {
            "basic": demo_basic_routing,
            "cross-method": demo_cross_method,
            "cross-border": demo_cross_border,
            "preferences": demo_receiver_preferences,
            "recovery": demo_failure_recovery,
            "lifecycle": demo_transaction_lifecycle,
            "graph": demo_payment_graph,
            "batch": demo_multi_intent_batch,
            "interactive": interactive_mode,
            "all": None,
        }
        if command == "all":
            demo_basic_routing(engine)
            demo_cross_method(engine)
            demo_cross_border(engine)
            demo_receiver_preferences(engine)
            demo_failure_recovery(engine)
            demo_transaction_lifecycle(engine)
            demo_payment_graph(engine)
            demo_multi_intent_batch(engine)
        elif command in demos:
            demos[command](engine)
        else:
            print(f"  Unknown command: {command}")
            print(f"  Available: {', '.join(demos.keys())}")
    else:
        # Run all demos by default
        demo_basic_routing(engine)
        demo_cross_method(engine)
        demo_cross_border(engine)
        demo_receiver_preferences(engine)
        demo_failure_recovery(engine)
        demo_transaction_lifecycle(engine)
        demo_payment_graph(engine)
        demo_multi_intent_batch(engine)


if __name__ == "__main__":
    main()
