"""Provider abstraction layer — simulated payment providers for India and cross-border."""

from __future__ import annotations

from .models import (
    Currency,
    PaymentMethod,
    PaymentMethodConfig,
    Provider,
    SettlementSpeed,
)


def build_razorpay() -> Provider:
    return Provider(
        id="razorpay",
        name="Razorpay",
        supported_methods=[
            PaymentMethod.UPI,
            PaymentMethod.VISA,
            PaymentMethod.MASTERCARD,
            PaymentMethod.RUPAY,
            PaymentMethod.NET_BANKING,
            PaymentMethod.WALLET,
        ],
        supported_currencies=[Currency.INR, Currency.USD, Currency.EUR, Currency.GBP, Currency.SGD],
        method_configs={
            PaymentMethod.UPI: PaymentMethodConfig(
                method=PaymentMethod.UPI,
                supported_currencies=[Currency.INR],
                settlement_speed= SettlementSpeed.INSTANT,
                fixed_fee=0.0,
                percentage_fee=0.002,
                min_amount=1.0,
                max_amount=100000.0,
                success_rate=0.987,
            ),
            PaymentMethod.VISA: PaymentMethodConfig(
                method=PaymentMethod.VISA,
                supported_currencies=[Currency.INR, Currency.USD, Currency.EUR, Currency.GBP],
                settlement_speed=SettlementSpeed.T_PLUS_2,
                fixed_fee=2.0,
                percentage_fee=0.02,
                min_amount=10.0,
                max_amount=500000.0,
                success_rate=0.961,
            ),
            PaymentMethod.MASTERCARD: PaymentMethodConfig(
                method=PaymentMethod.MASTERCARD,
                supported_currencies=[Currency.INR, Currency.USD, Currency.EUR, Currency.GBP],
                settlement_speed=SettlementSpeed.T_PLUS_2,
                fixed_fee=2.0,
                percentage_fee=0.02,
                min_amount=10.0,
                max_amount=500000.0,
                success_rate=0.958,
            ),
            PaymentMethod.RUPAY: PaymentMethodConfig(
                method=PaymentMethod.RUPAY,
                supported_currencies=[Currency.INR],
                settlement_speed=SettlementSpeed.T_PLUS_1,
                fixed_fee=1.0,
                percentage_fee=0.012,
                min_amount=10.0,
                max_amount=200000.0,
                success_rate=0.972,
            ),
            PaymentMethod.NET_BANKING: PaymentMethodConfig(
                method=PaymentMethod.NET_BANKING,
                supported_currencies=[Currency.INR],
                settlement_speed=SettlementSpeed.T_PLUS_1,
                fixed_fee=5.0,
                percentage_fee=0.005,
                min_amount=100.0,
                max_amount=1000000.0,
                success_rate=0.935,
            ),
            PaymentMethod.WALLET: PaymentMethodConfig(
                method=PaymentMethod.WALLET,
                supported_currencies=[Currency.INR],
                settlement_speed=SettlementSpeed.INSTANT,
                fixed_fee=0.0,
                percentage_fee=0.015,
                min_amount=1.0,
                max_amount=50000.0,
                success_rate=0.978,
            ),
        },
        settlement_speed=SettlementSpeed.T_PLUS_1,
        api_latency_ms=180.0,
    )


def build_cashfree() -> Provider:
    return Provider(
        id="cashfree",
        name="Cashfree Payments",
        supported_methods=[
            PaymentMethod.UPI,
            PaymentMethod.VISA,
            PaymentMethod.MASTERCARD,
            PaymentMethod.RUPAY,
            PaymentMethod.BANK_TRANSFER,
            PaymentMethod.WALLET,
        ],
        supported_currencies=[Currency.INR, Currency.USD, Currency.EUR, Currency.SGD, Currency.AED],
        method_configs={
            PaymentMethod.UPI: PaymentMethodConfig(
                method=PaymentMethod.UPI,
                supported_currencies=[Currency.INR],
                settlement_speed=SettlementSpeed.INSTANT,
                fixed_fee=0.0,
                percentage_fee=0.0015,
                min_amount=1.0,
                max_amount=100000.0,
                success_rate=0.991,
            ),
            PaymentMethod.VISA: PaymentMethodConfig(
                method=PaymentMethod.VISA,
                supported_currencies=[Currency.INR, Currency.USD, Currency.EUR],
                settlement_speed=SettlementSpeed.T_PLUS_1,
                fixed_fee=1.5,
                percentage_fee=0.018,
                min_amount=10.0,
                max_amount=500000.0,
                success_rate=0.965,
            ),
            PaymentMethod.MASTERCARD: PaymentMethodConfig(
                method=PaymentMethod.MASTERCARD,
                supported_currencies=[Currency.INR, Currency.USD, Currency.EUR],
                settlement_speed=SettlementSpeed.T_PLUS_1,
                fixed_fee=1.5,
                percentage_fee=0.018,
                min_amount=10.0,
                max_amount=500000.0,
                success_rate=0.962,
            ),
            PaymentMethod.RUPAY: PaymentMethodConfig(
                method=PaymentMethod.RUPAY,
                supported_currencies=[Currency.INR],
                settlement_speed=SettlementSpeed.T_PLUS_1,
                fixed_fee=1.0,
                percentage_fee=0.01,
                min_amount=10.0,
                max_amount=200000.0,
                success_rate=0.975,
            ),
            PaymentMethod.BANK_TRANSFER: PaymentMethodConfig(
                method=PaymentMethod.BANK_TRANSFER,
                supported_currencies=[Currency.INR],
                settlement_speed=SettlementSpeed.T_PLUS_1,
                fixed_fee=3.0,
                percentage_fee=0.003,
                min_amount=500.0,
                max_amount=5000000.0,
                success_rate=0.985,
            ),
            PaymentMethod.WALLET: PaymentMethodConfig(
                method=PaymentMethod.WALLET,
                supported_currencies=[Currency.INR],
                settlement_speed=SettlementSpeed.INSTANT,
                fixed_fee=0.0,
                percentage_fee=0.012,
                min_amount=1.0,
                max_amount=50000.0,
                success_rate=0.980,
            ),
        },
        settlement_speed=SettlementSpeed.T_PLUS_1,
        api_latency_ms=150.0,
    )


def build_payu() -> Provider:
    return Provider(
        id="payu",
        name="PayU India",
        supported_methods=[
            PaymentMethod.UPI,
            PaymentMethod.VISA,
            PaymentMethod.MASTERCARD,
            PaymentMethod.RUPAY,
            PaymentMethod.NET_BANKING,
            PaymentMethod.WALLET,
        ],
        supported_currencies=[Currency.INR, Currency.USD, Currency.EUR, Currency.GBP],
        method_configs={
            PaymentMethod.UPI: PaymentMethodConfig(
                method=PaymentMethod.UPI,
                supported_currencies=[Currency.INR],
                settlement_speed=SettlementSpeed.INSTANT,
                fixed_fee=0.0,
                percentage_fee=0.002,
                min_amount=1.0,
                max_amount=100000.0,
                success_rate=0.985,
            ),
            PaymentMethod.VISA: PaymentMethodConfig(
                method=PaymentMethod.VISA,
                supported_currencies=[Currency.INR, Currency.USD, Currency.EUR],
                settlement_speed=SettlementSpeed.T_PLUS_2,
                fixed_fee=2.5,
                percentage_fee=0.022,
                min_amount=10.0,
                max_amount=500000.0,
                success_rate=0.955,
            ),
            PaymentMethod.MASTERCARD: PaymentMethodConfig(
                method=PaymentMethod.MASTERCARD,
                supported_currencies=[Currency.INR, Currency.USD, Currency.EUR],
                settlement_speed=SettlementSpeed.T_PLUS_2,
                fixed_fee=2.5,
                percentage_fee=0.022,
                min_amount=10.0,
                max_amount=500000.0,
                success_rate=0.952,
            ),
            PaymentMethod.NET_BANKING: PaymentMethodConfig(
                method=PaymentMethod.NET_BANKING,
                supported_currencies=[Currency.INR],
                settlement_speed=SettlementSpeed.T_PLUS_1,
                fixed_fee=4.0,
                percentage_fee=0.004,
                min_amount=100.0,
                max_amount=1000000.0,
                success_rate=0.930,
            ),
        },
        settlement_speed=SettlementSpeed.T_PLUS_2,
        api_latency_ms=220.0,
    )


def build_upi_npci() -> Provider:
    """Simulated NPCI UPI rail — the interoperability backbone."""
    return Provider(
        id="upi_npci",
        name="UPI (NPCI)",
        supported_methods=[PaymentMethod.UPI],
        supported_currencies=[Currency.INR],
        method_configs={
            PaymentMethod.UPI: PaymentMethodConfig(
                method=PaymentMethod.UPI,
                supported_currencies=[Currency.INR],
                settlement_speed=SettlementSpeed.INSTANT,
                fixed_fee=0.0,
                percentage_fee=0.0,
                min_amount=1.0,
                max_amount=100000.0,
                success_rate=0.995,
            ),
        },
        settlement_speed=SettlementSpeed.INSTANT,
        api_latency_ms=80.0,
    )


def build_paypal_intl() -> Provider:
    return Provider(
        id="paypal_intl",
        name="PayPal International",
        supported_methods=[PaymentMethod.PAYPAL, PaymentMethod.VISA, PaymentMethod.MASTERCARD],
        supported_currencies=[Currency.USD, Currency.EUR, Currency.GBP, Currency.SGD, Currency.INR],
        method_configs={
            PaymentMethod.PAYPAL: PaymentMethodConfig(
                method=PaymentMethod.PAYPAL,
                supported_currencies=[Currency.USD, Currency.EUR, Currency.GBP, Currency.SGD],
                settlement_speed=SettlementSpeed.T_PLUS_1,
                fixed_fee=5.0,
                percentage_fee=0.035,
                min_amount=1.0,
                max_amount=10000.0,
                success_rate=0.970,
            ),
            PaymentMethod.VISA: PaymentMethodConfig(
                method=PaymentMethod.VISA,
                supported_currencies=[Currency.USD, Currency.EUR, Currency.GBP, Currency.SGD],
                settlement_speed=SettlementSpeed.T_PLUS_2,
                fixed_fee=3.0,
                percentage_fee=0.029,
                min_amount=1.0,
                max_amount=10000.0,
                success_rate=0.960,
            ),
            PaymentMethod.MASTERCARD: PaymentMethodConfig(
                method=PaymentMethod.MASTERCARD,
                supported_currencies=[Currency.USD, Currency.EUR, Currency.GBP, Currency.SGD],
                settlement_speed=SettlementSpeed.T_PLUS_2,
                fixed_fee=3.0,
                percentage_fee=0.029,
                min_amount=1.0,
                max_amount=10000.0,
                success_rate=0.958,
            ),
        },
        settlement_speed=SettlementSpeed.T_PLUS_1,
        api_latency_ms=350.0,
    )


# ── FX Rates (simulated) ─────────────────────────────────────────────────────

FX_RATES: dict[tuple[Currency, Currency], float] = {
    (Currency.INR, Currency.INR): 1.0,
    (Currency.USD, Currency.USD): 1.0,
    (Currency.EUR, Currency.EUR): 1.0,
    (Currency.GBP, Currency.GBP): 1.0,
    (Currency.SGD, Currency.SGD): 1.0,
    (Currency.AED, Currency.AED): 1.0,
    (Currency.USD, Currency.INR): 83.50,
    (Currency.INR, Currency.USD): 1.0 / 83.50,
    (Currency.EUR, Currency.INR): 91.00,
    (Currency.INR, Currency.EUR): 1.0 / 91.00,
    (Currency.GBP, Currency.INR): 106.00,
    (Currency.INR, Currency.GBP): 1.0 / 106.00,
    (Currency.SGD, Currency.INR): 62.50,
    (Currency.INR, Currency.SGD): 1.0 / 62.50,
    (Currency.AED, Currency.INR): 22.70,
    (Currency.INR, Currency.AED): 1.0 / 22.70,
    (Currency.USD, Currency.EUR): 0.92,
    (Currency.EUR, Currency.USD): 1.0 / 0.92,
    (Currency.USD, Currency.GBP): 0.79,
    (Currency.GBP, Currency.USD): 1.0 / 0.79,
    (Currency.USD, Currency.SGD): 1.34,
    (Currency.SGD, Currency.USD): 1.0 / 1.34,
    (Currency.USD, Currency.AED): 3.67,
    (Currency.AED, Currency.USD): 1.0 / 3.67,
}

# Spread on top of mid-market rate (simulated)
FX_SPREAD = 0.003  # 0.3%


def get_fx_rate(from_currency: Currency, to_currency: Currency) -> tuple[float, float]:
    """Returns (rate, spread_cost_pct). Rate converts from->to."""
    if from_currency == to_currency:
        return 1.0, 0.0
    rate = FX_RATES.get((from_currency, to_currency), 0.0)
    return rate, FX_SPREAD if rate > 0 else 0.0


# ── Provider Registry ──────────────────────────────────────────────────────────

class ProviderRegistry:
    """Registry of all available payment providers."""

    def __init__(self) -> None:
        self._providers: dict[str, Provider] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        for provider in [
            build_razorpay(),
            build_cashfree(),
            build_payu(),
            build_upi_npci(),
            build_paypal_intl(),
        ]:
            self._providers[provider.id] = provider

    def register(self, provider: Provider) -> None:
        self._providers[provider.id] = provider

    def get(self, provider_id: str) -> Provider | None:
        return self._providers.get(provider_id)

    def all(self) -> list[Provider]:
        return list(self._providers.values())

    def find_by_method(self, method: PaymentMethod) -> list[Provider]:
        return [p for p in self._providers.values() if p.supports_method(method)]

    def find_by_currency(self, currency: Currency) -> list[Provider]:
        return [p for p in self._providers.values() if p.supports_currency(currency)]

    def find_capable(self, method: PaymentMethod, currency: Currency) -> list[Provider]:
        return [
            p for p in self._providers.values()
            if p.supports_method(method) and p.supports_currency(currency)
        ]
