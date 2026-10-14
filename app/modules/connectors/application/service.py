from __future__ import annotations

from uuid import UUID

from app.modules.connectors.application.ports import ConnectorRepository
from app.modules.connectors.application.registry import ConnectorProviderRegistry
from app.modules.connectors.domain.models import (
    Connector,
    ConnectorKind,
    ConnectorStatus,
)
from app.shared.domain.errors import BusinessRuleViolation


class ConnectorService:
    def __init__(
        self,
        repository: ConnectorRepository,
        registry: ConnectorProviderRegistry | None = None,
    ):
        self.repository = repository
        self.registry = registry

    def register(
        self,
        *,
        tenant_id: UUID,
        name: str,
        kind: ConnectorKind,
        endpoint: str,
    ) -> Connector:
        connector = Connector.create(
            tenant_id=tenant_id,
            name=name,
            kind=kind,
            endpoint=endpoint,
        )
        self.repository.save(connector)
        return connector

    def get(
        self,
        *,
        tenant_id: UUID,
        connector_id: UUID,
    ) -> Connector | None:
        return self.repository.get(tenant_id, connector_id)

    def list(
        self,
        *,
        tenant_id: UUID,
    ) -> tuple[Connector, ...]:
        return self.repository.list(tenant_id)

    def set_status(
        self,
        *,
        tenant_id: UUID,
        connector_id: UUID,
        status: ConnectorStatus,
    ) -> Connector:
        connector = self.repository.get(tenant_id, connector_id)

        if connector is None:
            raise BusinessRuleViolation("connector not found")

        updated = Connector(
            id=connector.id,
            tenant_id=connector.tenant_id,
            name=connector.name,
            kind=connector.kind,
            status=ConnectorStatus(status),
            endpoint=connector.endpoint,
            created_at=connector.created_at,
        )

        self.repository.save(updated)
        return updated

    def send(
        self,
        *,
        tenant_id: UUID,
        connector_id: UUID,
        payload: dict,
    ) -> None:
        if self.registry is None:
            raise BusinessRuleViolation("connector provider registry is not configured")

        connector = self.repository.get(tenant_id, connector_id)

        if connector is None:
            raise BusinessRuleViolation("connector not found")

        provider = self.registry.get(connector.kind)
        provider.send(connector, payload=payload)

    def remove(
        self,
        *,
        tenant_id: UUID,
        connector_id: UUID,
    ) -> None:
        self.repository.delete(tenant_id, connector_id)
