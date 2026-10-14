from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID, uuid4

from app.shared.domain.errors import BusinessRuleViolation


class ConnectorStatus(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class ConnectorKind(str, Enum):
    GENERIC_HTTP = "generic_http"
    WEBHOOK = "webhook"


@dataclass(frozen=True)
class Connector:
    id: UUID
    tenant_id: UUID
    name: str
    kind: ConnectorKind
    status: ConnectorStatus
    endpoint: str
    created_at: object

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        name: str,
        kind: ConnectorKind,
        endpoint: str,
        status: ConnectorStatus = ConnectorStatus.ENABLED,
    ) -> "Connector":
        if not isinstance(tenant_id, UUID):
            raise BusinessRuleViolation("tenant_id must be a UUID")

        if not isinstance(name, str) or not name.strip():
            raise BusinessRuleViolation("name must not be empty")

        if not isinstance(kind, ConnectorKind):
            try:
                kind = ConnectorKind(kind)
            except (TypeError, ValueError) as exc:
                raise BusinessRuleViolation("invalid connector kind") from exc

        if not isinstance(status, ConnectorStatus):
            try:
                status = ConnectorStatus(status)
            except (TypeError, ValueError) as exc:
                raise BusinessRuleViolation("invalid connector status") from exc

        if not isinstance(endpoint, str) or not endpoint.strip():
            raise BusinessRuleViolation("endpoint must not be empty")

        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            name=name.strip(),
            kind=kind,
            status=status,
            endpoint=endpoint.strip(),
            created_at=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ),
        )
