import pytest

from app.modules.connectors.application.registry import ConnectorProviderRegistry
from app.modules.connectors.domain.models import ConnectorKind
from app.shared.domain.errors import BusinessRuleViolation


class FakeProvider:
    def send(self, connector, *, payload):
        pass


def test_register_and_get_provider():
    registry = ConnectorProviderRegistry()
    provider = FakeProvider()

    registry.register(ConnectorKind.GENERIC_HTTP, provider)

    assert registry.get(ConnectorKind.GENERIC_HTTP) is provider
    assert registry.has(ConnectorKind.GENERIC_HTTP) is True


def test_register_accepts_string_kind():
    registry = ConnectorProviderRegistry()
    provider = FakeProvider()

    registry.register("generic_http", provider)

    assert registry.get("generic_http") is provider


def test_duplicate_provider_registration_is_rejected():
    registry = ConnectorProviderRegistry()
    provider = FakeProvider()

    registry.register(ConnectorKind.GENERIC_HTTP, provider)

    with pytest.raises(
        BusinessRuleViolation,
        match="provider already registered",
    ):
        registry.register(ConnectorKind.GENERIC_HTTP, FakeProvider())


def test_missing_provider_is_rejected():
    registry = ConnectorProviderRegistry()

    with pytest.raises(
        BusinessRuleViolation,
        match="no provider registered",
    ):
        registry.get(ConnectorKind.GENERIC_HTTP)


def test_invalid_kind_is_rejected():
    registry = ConnectorProviderRegistry()

    with pytest.raises(
        BusinessRuleViolation,
        match="unsupported connector kind",
    ):
        registry.register("invalid-kind", FakeProvider())


def test_has_returns_false_for_invalid_or_unregistered_kind():
    registry = ConnectorProviderRegistry()

    assert registry.has(ConnectorKind.GENERIC_HTTP) is False
    assert registry.has("invalid-kind") is False
