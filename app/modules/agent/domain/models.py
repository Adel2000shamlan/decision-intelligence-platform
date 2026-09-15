from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class Agent:
    id: UUID
    tenant_id: UUID
    name: str
    capabilities: frozenset[str]
    enabled: bool = True
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @classmethod
    def register(
        cls,
        tenant_id,
        name,
        capabilities=(),
    ) -> "Agent":
        tenant = UUID(str(tenant_id))

        if not isinstance(name, str) or not name.strip():
            raise ValueError("agent name required")

        normalized = frozenset(
            str(capability).strip()
            for capability in capabilities
            if str(capability).strip()
        )

        return cls(
            id=uuid4(),
            tenant_id=tenant,
            name=name.strip(),
            capabilities=normalized,
        )

    def disable(self) -> "Agent":
        return Agent(
            id=self.id,
            tenant_id=self.tenant_id,
            name=self.name,
            capabilities=self.capabilities,
            enabled=False,
            created_at=self.created_at,
        )

    def enable(self) -> "Agent":
        return Agent(
            id=self.id,
            tenant_id=self.tenant_id,
            name=self.name,
            capabilities=self.capabilities,
            enabled=True,
            created_at=self.created_at,
        )

    def with_capabilities(self, capabilities) -> "Agent":
        normalized = frozenset(
            str(capability).strip()
            for capability in capabilities
            if str(capability).strip()
        )

        return Agent(
            id=self.id,
            tenant_id=self.tenant_id,
            name=self.name,
            capabilities=normalized,
            enabled=self.enabled,
            created_at=self.created_at,
        )
