from __future__ import annotations

import ipaddress
from typing import Callable
from urllib.parse import urlparse

from app.modules.connectors.application.ports import ConnectorProvider
from app.modules.connectors.domain.models import Connector, ConnectorKind, ConnectorStatus
from app.shared.domain.errors import BusinessRuleViolation


def _validate_endpoint(endpoint: str) -> None:
    parsed = urlparse(endpoint)

    if parsed.scheme.lower() != "https":
        raise BusinessRuleViolation("connector endpoint must use HTTPS")

    if not parsed.hostname:
        raise BusinessRuleViolation("connector endpoint must contain a hostname")

    hostname = parsed.hostname.lower().rstrip(".")

    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise BusinessRuleViolation("connector endpoint cannot target localhost")

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None

    if address is not None and (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_unspecified
    ):
        raise BusinessRuleViolation("connector endpoint cannot target a private or local address")


class GenericHttpConnectorProvider(ConnectorProvider):
    def __init__(self, transport: Callable[[str, dict], None]):
        self.transport = transport

    def send(self, connector: Connector, *, payload: dict) -> None:
        if connector.kind is not ConnectorKind.GENERIC_HTTP:
            raise BusinessRuleViolation(
                "connector kind is not supported by generic HTTP provider"
            )

        if connector.status is not ConnectorStatus.ENABLED:
            raise BusinessRuleViolation("connector is disabled")

        if not isinstance(payload, dict):
            raise BusinessRuleViolation("payload must be a dictionary")

        _validate_endpoint(connector.endpoint)

        self.transport(connector.endpoint, payload)
