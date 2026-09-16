"""Tests for API module."""

from unipay_router.api import UniPayAPI


class TestUniPayAPI:
    def setup_method(self):
        self.api = UniPayAPI()
        # Register a test receiver for payment intent tests
        self.api.create_receiver_preference({
            "receiver_id": "test_receiver",
            "handle": "test@unipay",
            "country": "IN",
            "currency": "INR",
            "preferred_methods": ["upi"],
        })

    def test_health_check(self):
        result = self.api.health_check()
        assert result["status"] == "ok"
        assert "providers" in result
        assert "receivers" in result

    def test_create_payment_intent(self):
        result = self.api.create_payment_intent({
            "amount": 10000,
            "currency": "INR",
            "receiver_handle": "test@unipay",
            "sender": {
                "country": "IN",
                "preferred_methods": ["upi"],
            },
        })
        assert "id" in result
        assert result["amount"] == 10000
        assert result["currency"] == "INR"

    def test_create_payment_intent_invalid_currency(self):
        result = self.api.create_payment_intent({
            "amount": 10000,
            "currency": "INVALID",
            "receiver_handle": "test@unipay",
        })
        assert "error" in result

    def test_create_payment_intent_rejects_non_positive_amount(self):
        result = self.api.create_payment_intent({
            "amount": 0,
            "currency": "INR",
            "receiver_handle": "test@unipay",
        })
        assert result["error"] == "amount must be a positive finite number"

    def test_confirm_payment_intent_is_explicitly_simulated(self):
        result = self.api.create_payment_intent({
            "amount": 1000,
            "currency": "INR",
            "receiver_handle": "test@unipay",
            "sender": {"preferred_methods": ["upi"]},
        })
        confirmed = self.api.confirm_payment_intent(result["id"])
        assert confirmed["state"] == "settled"
        assert confirmed["simulated"] is True

    def test_create_receiver_preference(self):
        result = self.api.create_receiver_preference({
            "receiver_id": "test_user",
            "handle": "new_user@unipay",
            "country": "IN",
            "currency": "INR",
            "preferred_methods": ["upi"],
        })
        assert result["handle"] == "new_user@unipay"
        assert result["receiver_id"] == "test_user"

    def test_resolve_handle(self):
        result = self.api.resolve_handle("test@unipay")
        assert result["receiver_id"] == "test_receiver"
        assert "upi" in result.get("preferred_methods", [])

    def test_resolve_handle_not_found(self):
        result = self.api.resolve_handle("unknown@unipay")
        assert "error" in result

    def test_list_routes(self):
        result = self.api.list_routes({
            "amount": 10000,
            "currency": "INR",
            "receiver_handle": "test@unipay",
        })
        assert "routes" in result
        assert "count" in result

    def test_get_fx_rate(self):
        result = self.api.get_fx_rate("USD", "INR")
        assert result["from"] == "USD"
        assert result["to"] == "INR"
        assert "rate" in result
        assert result["rate"] > 0

    def test_graph_stats(self):
        result = self.api.get_graph_stats()
        assert "total_nodes" in result
        assert "total_edges" in result
