from __future__ import annotations

from app.modules.connectors.application.ports import ConnectorProvider
from app.modules.connectors.domain.models import ConnectorKind
from app.shared.domain.errors import BusinessRuleViolation


class ConnectorProviderRegistry:
    def __init__(self):
        self._providers: dict[ConnectorKind, ConnectorProvider] = {}

    def register(
        self,
        kind: ConnectorKind,
        provider: ConnectorProvider,
    ) -> None:
        try:
            normalized_kind = ConnectorKind(kind)
        except (TypeError, ValueError) as exc:
            raise BusinessRuleViolation("unsupported connector kind") from exc

        if normalized_kind in self._providers:
            raise BusinessRuleViolation(
                "connector provider already registered"
            )

        self._providers[normalized_kind] = provider

    def get(self, kind: ConnectorKind) -> ConnectorProvider:
        try:
            normalized_kind = ConnectorKind(kind)
        except (TypeError, ValueError) as exc:
            raise BusinessRuleViolation("unsupported connector kind") from exc

        provider = self._providers.get(normalized_kind)

        if provider is None:
            raise BusinessRuleViolation(
                "no provider registered for connector kind"
            )

        return provider

    def has(self, kind: ConnectorKind) -> bool:
        try:
            normalized_kind = ConnectorKind(kind)
        except (TypeError, ValueError):
            return False

        return normalized_kind in self._providers
