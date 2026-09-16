"""Reconciliation Engine — the 'boring' moat that becomes valuable at scale.

Tracks transaction states across providers, identifies mismatches,
and provides a unified view of payment status.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from .models import RouteCandidate, TransactionState


@dataclass
class ReconciliationRecord:
    """A single reconciliation record for a transaction."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    payment_intent_id: str = ""
    provider_payment_id: str = ""
    provider: str = ""
    amount: int = 0
    currency: str = "INR"
    provider_status: str = ""
    our_status: TransactionState = TransactionState.CREATED
    last_synced_at: float = 0.0
    created_at: float = field(default_factory=time.time)
    discrepancy: str | None = None


class ReconciliationEngine:
    """Tracks and reconciles transactions across payment providers.

    The reconciliation layer is what enterprise merchants actually need.
    It answers: "Where the hell did this payment go?"
    """

    def __init__(self) -> None:
        self._records: dict[str, ReconciliationRecord] = {}
        self._by_intent: dict[str, list[str]] = {}  # intent_id -> [record_ids]
        self._by_provider: dict[str, list[str]] = {}  # provider -> [record_ids]

    def create_record(
        self,
        payment_intent_id: str,
        provider: str,
        amount: int,
        currency: str,
        route: RouteCandidate | None = None,
    ) -> ReconciliationRecord:
        """Create a new reconciliation record."""
        record = ReconciliationRecord(
            payment_intent_id=payment_intent_id,
            provider=provider,
            amount=amount,
            currency=currency,
            our_status=TransactionState.PAYMENT_INITIATED,
        )
        self._records[record.id] = record
        self._by_intent.setdefault(payment_intent_id, []).append(record.id)
        self._by_provider.setdefault(provider, []).append(record.id)
        return record

    def update_from_provider(
        self,
        record_id: str,
        provider_status: str,
        provider_payment_id: str = "",
    ) -> ReconciliationRecord | None:
        """Update record from provider webhook data."""
        record = self._records.get(record_id)
        if not record:
            return None

        record.provider_status = provider_status
        record.provider_payment_id = provider_payment_id
        record.last_synced_at = time.time()

        # Map provider status to our status
        status_map = {
            "authorized": TransactionState.PAYMENT_SUCCESS,
            "captured": TransactionState.SETTLED,
            "failed": TransactionState.PAYMENT_FAILED,
            "refunded": TransactionState.REFUNDED,
            "pending": TransactionState.PAYMENT_PROCESSING,
            "processing": TransactionState.PAYMENT_PROCESSING,
            "success": TransactionState.SETTLED,
            "failure": TransactionState.PAYMENT_FAILED,
        }
        new_status = status_map.get(provider_status.lower(), record.our_status)
        record.our_status = new_status

        # Check for discrepancy
        record.discrepancy = self._check_discrepancy(record)

        return record

    def _check_discrepancy(self, record: ReconciliationRecord) -> str | None:
        """Check if there's a discrepancy between our state and provider state."""
        if not record.provider_status:
            return None

        # Status mismatch
        provider_lower = record.provider_status.lower()
        if record.our_status == TransactionState.SETTLED and provider_lower not in ("captured", "success"):
            return f"We think settled, provider says: {record.provider_status}"
        if record.our_status == TransactionState.PAYMENT_FAILED and provider_lower not in ("failed", "failure"):
            return f"We think failed, provider says: {record.provider_status}"
        if record.our_status == TransactionState.PAYMENT_PROCESSING and provider_lower in ("captured", "success"):
            return f"We think processing, provider says: {record.provider_status}"

        return None

    def get_record(self, record_id: str) -> ReconciliationRecord | None:
        return self._records.get(record_id)

    def get_by_intent(self, payment_intent_id: str) -> list[ReconciliationRecord]:
        record_ids = self._by_intent.get(payment_intent_id, [])
        return [self._records[rid] for rid in record_ids if rid in self._records]

    def get_by_provider(self, provider: str) -> list[ReconciliationRecord]:
        record_ids = self._by_provider.get(provider, [])
        return [self._records[rid] for rid in record_ids if rid in self._records]

    def get_discrepancies(self) -> list[ReconciliationRecord]:
        """Get all records with discrepancies (needs attention)."""
        return [r for r in self._records.values() if r.discrepancy]

    def get_unsettled(self) -> list[ReconciliationRecord]:
        """Get all records that haven't settled yet."""
        unsettled_states = {
            TransactionState.CREATED,
            TransactionState.INTENT_VALIDATED,
            TransactionState.ROUTE_SELECTED,
            TransactionState.PAYMENT_INITIATED,
            TransactionState.PAYMENT_PROCESSING,
            TransactionState.SETTLEMENT_PENDING,
        }
        return [r for r in self._records.values() if r.our_status in unsettled_states]

    def get_stats(self) -> dict:
        """Get reconciliation statistics."""
        total = len(self._records)
        settled = sum(1 for r in self._records.values() if r.our_status == TransactionState.SETTLED)
        failed = sum(1 for r in self._records.values() if r.our_status == TransactionState.PAYMENT_FAILED)
        discrepancies = len(self.get_discrepancies())
        unsettled = len(self.get_unsettled())

        by_provider: dict[str, dict] = {}
        for record in self._records.values():
            provider = record.provider
            if provider not in by_provider:
                by_provider[provider] = {"total": 0, "settled": 0, "failed": 0}
            by_provider[provider]["total"] += 1
            if record.our_status == TransactionState.SETTLED:
                by_provider[provider]["settled"] += 1
            elif record.our_status == TransactionState.PAYMENT_FAILED:
                by_provider[provider]["failed"] += 1

        return {
            "total_transactions": total,
            "settled": settled,
            "failed": failed,
            "unsettled": unsettled,
            "discrepancies": discrepancies,
            "settlement_rate": settled / total if total > 0 else 0,
            "by_provider": by_provider,
        }

    def to_dict(self, record_id: str) -> dict | None:
        record = self._records.get(record_id)
        if not record:
            return None
        return {
            "id": record.id,
            "payment_intent_id": record.payment_intent_id,
            "provider": record.provider,
            "amount": record.amount,
            "currency": record.currency,
            "provider_status": record.provider_status,
            "our_status": record.our_status.value,
            "discrepancy": record.discrepancy,
            "last_synced_at": record.last_synced_at,
            "created_at": record.created_at,
        }
