from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.connectors.domain.models import Connector, ConnectorStatus


class ConnectorRepository(Protocol):
    def save(self, connector: Connector) -> None: ...

    def get(self, tenant_id: UUID, connector_id: UUID) -> Connector | None: ...

    def list(self, tenant_id: UUID) -> tuple[Connector, ...]: ...

    def delete(self, tenant_id: UUID, connector_id: UUID) -> None: ...


class ConnectorProvider(Protocol):
    def send(
        self,
        connector: Connector,
        *,
        payload: dict,
    ) -> None: ...


class ConnectorApplicationPort(Protocol):
    def get_connector(
        self,
        tenant_id: UUID,
        connector_id: UUID,
    ) -> Connector | None: ...

    def set_status(
        self,
        tenant_id: UUID,
        connector_id: UUID,
        status: ConnectorStatus,
    ) -> Connector: ...
