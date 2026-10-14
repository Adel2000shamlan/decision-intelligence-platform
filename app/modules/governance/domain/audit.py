from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Mapping
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GovernanceAuditRecord:
    sequence: int
    tenant_id: UUID
    correlation_id: UUID
    action: str
    actor_id: UUID | None
    subject_id: UUID | None
    occurred_at: datetime
    payload: tuple[tuple[str, str], ...]
    previous_hash: str
    record_hash: str


class GovernanceAuditLog:
    """
    Tamper-evident, tenant-aware governance audit log.

    Payload is deliberately string-only and validated against secret names
    before persistence.
    """

    _FORBIDDEN = frozenset(
        {
            "password",
            "password_hash",
            "access_token",
            "refresh_token",
            "api_key",
            "private_key",
            "otp_secret",
            "secret",
            "credential",
        }
    )

    def __init__(self) -> None:
        self.records: list[GovernanceAuditRecord] = []

    @classmethod
    def _safe_payload(
        cls, payload: Mapping[str, object] | None
    ) -> tuple[tuple[str, str], ...]:
        source = payload or {}
        safe: list[tuple[str, str]] = []

        for key, value in source.items():
            normalized = str(key).lower()
            if normalized in cls._FORBIDDEN:
                raise ValueError("governance audit secret boundary violation")
            safe.append((str(key), str(value)))

        return tuple(sorted(safe))

    @staticmethod
    def _hash_record(
        *,
        sequence: int,
        tenant_id: UUID,
        correlation_id: UUID,
        action: str,
        actor_id: UUID | None,
        subject_id: UUID | None,
        occurred_at: datetime,
        payload: tuple[tuple[str, str], ...],
        previous_hash: str,
    ) -> str:
        raw = json.dumps(
            {
                "sequence": sequence,
                "tenant_id": str(tenant_id),
                "correlation_id": str(correlation_id),
                "action": action,
                "actor_id": str(actor_id) if actor_id else None,
                "subject_id": str(subject_id) if subject_id else None,
                "occurred_at": occurred_at.isoformat(),
                "payload": list(payload),
                "previous_hash": previous_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        return hashlib.sha256(raw).hexdigest()

    def append(
        self,
        *,
        tenant_id: UUID,
        correlation_id: UUID,
        action: str,
        actor_id: UUID | None = None,
        subject_id: UUID | None = None,
        payload: Mapping[str, object] | None = None,
    ) -> GovernanceAuditRecord:
        safe_payload = self._safe_payload(payload)
        previous_hash = (
            self.records[-1].record_hash if self.records else "GENESIS"
        )
        sequence = len(self.records) + 1
        occurred_at = datetime.now(timezone.utc)

        record_hash = self._hash_record(
            sequence=sequence,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            action=action,
            actor_id=actor_id,
            subject_id=subject_id,
            occurred_at=occurred_at,
            payload=safe_payload,
            previous_hash=previous_hash,
        )

        record = GovernanceAuditRecord(
            sequence=sequence,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            action=action,
            actor_id=actor_id,
            subject_id=subject_id,
            occurred_at=occurred_at,
            payload=safe_payload,
            previous_hash=previous_hash,
            record_hash=record_hash,
        )
        self.records.append(record)
        return record

    def verify(self) -> bool:
        previous_hash = "GENESIS"

        for record in self.records:
            if record.previous_hash != previous_hash:
                return False

            expected = self._hash_record(
                sequence=record.sequence,
                tenant_id=record.tenant_id,
                correlation_id=record.correlation_id,
                action=record.action,
                actor_id=record.actor_id,
                subject_id=record.subject_id,
                occurred_at=record.occurred_at,
                payload=record.payload,
                previous_hash=record.previous_hash,
            )

            if expected != record.record_hash:
                return False

            previous_hash = record.record_hash

        return True

    def for_tenant(self, tenant_id: UUID) -> tuple[GovernanceAuditRecord, ...]:
        return tuple(
            record for record in self.records if record.tenant_id == tenant_id
        )
