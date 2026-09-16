# Contributing

## Development Setup

```bash
# Clone the repo
git clone https://github.com/your-org/unipay-router.git
cd unipay-router

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dev dependencies
pip install -e ".[dev]"

# Start Hyperswitch
docker-compose up -d

# Run tests
pytest

# Run linter
ruff check unipay_router/
```

## Project Structure

```
unipay-router/
├── config/
│   └── hyperswitch.toml     # Hyperswitch connector config
├── unipay_router/
│   ├── __init__.py           # Package init + version
│   ├── models.py             # Core data models
│   ├── routing.py            # Routing engine
│   ├── providers.py          # Provider registry
│   ├── hyperswitch_client.py # Hyperswitch API client
│   ├── receiver_preferences.py # Receiver preference engine
│   ├── fx_engine.py          # FX rate engine
│   ├── payment_graph.py      # Payment graph model
│   ├── webhook_handler.py    # Webhook processing
│   ├── reconciliation.py     # Transaction reconciliation
│   ├── api.py                # REST API layer
│   └── cli.py                # CLI demo interface
├── tests/
│   ├── test_models.py
│   ├── test_routing.py
│   └── test_api.py
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── ROUTING.md
│   └── ...
├── docker-compose.yml
├── pyproject.toml
└── LICENSE
```

## Coding Standards

- **Type hints:** Always
- **Docstrings:** Google style
- **Line length:** 100 characters
- **Formatter:** Ruff
- **Linter:** Ruff

```python
# Good
def find_routes(
    intent: PaymentIntent,
    max_results: int = 5,
) -> list[RouteCandidate]:
    """Find optimal routes for a payment intent.

    Args:
        intent: The payment intent to route.
        max_results: Maximum routes to return.

    Returns:
        List of route candidates sorted by score.
    """
    ...
```

## Commit Messages

Use conventional commits:

```
feat: add new payment method support
fix: correct webhook signature verification
docs: update API reference
refactor: extract reconciliation engine
test: add unit tests for routing
```

## Pull Requests

1. Create a feature branch
2. Make your changes
3. Add tests
4. Ensure tests pass
5. Update documentation if needed
6. Submit PR

## Adding a New Provider

1. Add connector config to `config/hyperswitch.toml`
2. Update `unipay_router/providers.py` with provider details
3. Add webhook handler in `unipay_router/webhook_handler.py`
4. Add tests for the new provider
5. Update `PROVIDERS.md` with sandbox setup

## Adding a New Payment Method

1. Add enum value to `PaymentMethod` in `models.py`
2. Update provider configs in `providers.py`
3. Add scoring adjustments in `routing.py`
4. Update documentation
