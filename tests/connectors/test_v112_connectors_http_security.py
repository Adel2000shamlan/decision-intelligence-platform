from uuid import uuid4

import pytest

from app.modules.connectors.domain.models import Connector
from app.modules.connectors.infrastructure.http import GenericHttpConnectorProvider
from app.shared.domain.errors import BusinessRuleViolation


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://example.com/api",
        "http://localhost:8000/api",
        "http://127.0.0.1:8000/api",
        "http://169.254.169.254/latest/meta-data",
    ],
)
def test_unsafe_http_endpoints_are_rejected(endpoint):
    connector = Connector.create(
        tenant_id=uuid4(),
        name="unsafe",
        kind="generic_http",
        endpoint=endpoint,
    )

    provider = GenericHttpConnectorProvider(
        lambda endpoint, payload: None
    )

    with pytest.raises(BusinessRuleViolation):
        provider.send(connector, payload={"event": "test"})
