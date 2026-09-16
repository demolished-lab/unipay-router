"""FX Engine — live exchange rates via free APIs.

Uses multiple free providers with fallback:
1. exchangerate-api.com (1,500 req/month free)
2. CurrencyScoop (5,000 req/month free)
3. Fallback: hardcoded rates
"""

from __future__ import annotations

import time
from urllib.parse import urlparse
from dataclasses import dataclass

try:
    import httpx
except ImportError:
    import json
    import urllib.request
    httpx = None



# Fallback rates (used when APIs are unavailable)
FALLBACK_RATES: dict[tuple[str, str], float] = {
    ("INR", "INR"): 1.0,
    ("USD", "USD"): 1.0,
    ("EUR", "EUR"): 1.0,
    ("GBP", "GBP"): 1.0,
    ("SGD", "SGD"): 1.0,
    ("AED", "AED"): 1.0,
    ("USD", "INR"): 83.50,
    ("INR", "USD"): 1.0 / 83.50,
    ("EUR", "INR"): 91.00,
    ("INR", "EUR"): 1.0 / 91.00,
    ("GBP", "INR"): 106.00,
    ("INR", "GBP"): 1.0 / 106.00,
    ("SGD", "INR"): 62.50,
    ("INR", "SGD"): 1.0 / 62.50,
    ("AED", "INR"): 22.70,
    ("INR", "AED"): 1.0 / 22.70,
    ("USD", "EUR"): 0.92,
    ("EUR", "USD"): 1.0 / 0.92,
    ("USD", "GBP"): 0.79,
    ("GBP", "USD"): 1.0 / 0.79,
    ("USD", "SGD"): 1.34,
    ("SGD", "USD"): 1.0 / 1.34,
    ("USD", "AED"): 3.67,
    ("AED", "USD"): 1.0 / 3.67,
}

# Spread on top of mid-market rate
FX_SPREAD = 0.003  # 0.3%


@dataclass
class FXRate:
    from_currency: str
    to_currency: str
    rate: float
    spread: float
    source: str
    timestamp: float


class FXEngine:
    """Live FX rate engine with caching and fallback."""

    def __init__(self) -> None:
        self._cache: dict[str, FXRate] = {}
        self._cache_ttl = 300  # 5 minutes

    def get_rate(self, from_currency: str, to_currency: str) -> FXRate:
        """Get exchange rate with caching."""
        if from_currency == to_currency:
            return FXRate(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=1.0,
                spread=0.0,
                source="identity",
                timestamp=time.time(),
            )

        cache_key = f"{from_currency}:{to_currency}"
        cached = self._cache.get(cache_key)
        if cached and (time.time() - cached.timestamp) < self._cache_ttl:
            return cached

        # Try API providers
        rate = self._fetch_live_rate(from_currency, to_currency)
        if rate is None:
            rate = FALLBACK_RATES.get((from_currency, to_currency), 0.0)
            source = "fallback"
        else:
            source = "live"

        result = FXRate(
            from_currency=from_currency,
            to_currency=to_currency,
            rate=rate,
            spread=FX_SPREAD if rate > 0 else 0.0,
            source=source,
            timestamp=time.time(),
        )
        self._cache[cache_key] = result
        return result

    def _fetch_live_rate(self, from_currency: str, to_currency: str) -> float | None:
        """Try to fetch live rate from free APIs."""
        # Try exchangerate-api.com
        try:
            return self._fetch_exchangerate_api(from_currency, to_currency)
        except Exception:
            pass

        # Try CurrencyScoop
        try:
            return self._fetch_currencyscoop(from_currency, to_currency)
        except Exception:
            pass

        return None

    def _fetch_exchangerate_api(self, from_currency: str, to_currency: str) -> float | None:
        """Fetch from exchangerate-api.com (free tier: 1,500 req/month)."""
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
        data = self._http_get(url)
        if data and "rates" in data:
            return data["rates"].get(to_currency)
        return None

    def _fetch_currencyscoop(self, from_currency: str, to_currency: str) -> float | None:
        """Fetch from CurrencyScoop (free tier: 5,000 req/month)."""
        url = f"https://api.currencyscoop.com/v1/latest?api_key=demo&base={from_currency}&symbols={to_currency}"
        data = self._http_get(url)
        if data and "response" in data:
            rates = data["response"].get("rates", {})
            return rates.get(to_currency)
        return None

    def _http_get(self, url: str) -> dict | None:
        """HTTP GET with timeout."""
        try:
            if urlparse(url).scheme not in {"http", "https"}:
                return None
            if httpx:
                resp = httpx.get(url, timeout=10.0)
                return resp.json()
            else:
                req = urllib.request.Request(url, headers={"User-Agent": "UniPayRouter/0.1"})
                with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310 - scheme is allowlisted above
                    return json.loads(resp.read())
        except Exception:
            return None

    def calculate_fx_cost(self, amount: float, from_currency: str, to_currency: str) -> tuple[float, float]:
        """Calculate FX conversion cost. Returns (converted_amount, fx_cost)."""
        rate_info = self.get_rate(from_currency, to_currency)
        if rate_info.rate == 0:
            return (0.0, amount)  # No conversion possible

        fx_cost = amount * rate_info.spread
        converted = (amount - fx_cost) * rate_info.rate
        return (converted, fx_cost)

    def get_supported_pairs(self) -> list[tuple[str, str]]:
        """Get list of supported currency pairs."""
        pairs = list(FALLBACK_RATES.keys())
        return sorted(set(pairs))
