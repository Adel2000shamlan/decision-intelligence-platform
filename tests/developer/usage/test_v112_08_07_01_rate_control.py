from uuid import uuid4

import pytest

from app.infrastructure.gateway import RateLimiter
from app.modules.developer.usage.rate_control import (
    DeveloperRateController,
    DeveloperRateLimit,
)


def test_developer_rate_limit_uses_application_identity():
    tenant_id = uuid4()
    application_a = uuid4()
    application_b = uuid4()

    controller = DeveloperRateController(
        limiter=RateLimiter(limit=2, window=60),
    )

    assert controller.allow(
        tenant_id=tenant_id,
        application_id=application_a,
    )
    assert controller.allow(
        tenant_id=tenant_id,
        application_id=application_a,
    )
    assert not controller.allow(
        tenant_id=tenant_id,
        application_id=application_a,
    )

    # A different application must have an independent bucket.
    assert controller.allow(
        tenant_id=tenant_id,
        application_id=application_b,
    )


def test_developer_rate_limit_is_tenant_isolated():
    application_id = uuid4()
    tenant_a = uuid4()
    tenant_b = uuid4()

    controller = DeveloperRateController(
        limiter=RateLimiter(limit=1, window=60),
    )

    assert controller.allow(
        tenant_id=tenant_a,
        application_id=application_id,
    )
    assert not controller.allow(
        tenant_id=tenant_a,
        application_id=application_id,
    )

    # Same application UUID under another tenant is independent.
    assert controller.allow(
        tenant_id=tenant_b,
        application_id=application_id,
    )


def test_developer_rate_limit_rejects_invalid_identity():
    controller = DeveloperRateController(
        limiter=RateLimiter(limit=1, window=60),
    )

    with pytest.raises(ValueError):
        controller.allow(
            tenant_id="not-a-uuid",
            application_id=uuid4(),
        )

    with pytest.raises(ValueError):
        controller.allow(
            tenant_id=uuid4(),
            application_id="not-a-uuid",
        )


def test_developer_rate_limit_configuration_is_explicit():
    policy = DeveloperRateLimit(limit=10, window_seconds=30)

    assert policy.limit == 10
    assert policy.window_seconds == 30


def test_developer_rate_limit_rejects_invalid_configuration():
    with pytest.raises(ValueError):
        DeveloperRateLimit(limit=0, window_seconds=30)

    with pytest.raises(ValueError):
        DeveloperRateLimit(limit=10, window_seconds=0)


def test_developer_rate_limit_sliding_window(monkeypatch):
    from app.infrastructure import gateway

    current_time = 100.0
    monkeypatch.setattr(
        gateway.time,
        "monotonic",
        lambda: current_time,
    )

    controller = DeveloperRateController(
        limiter=RateLimiter(limit=2, window=60),
    )

    tenant_id = uuid4()
    application_id = uuid4()

    assert controller.allow(
        tenant_id=tenant_id,
        application_id=application_id,
    )
    assert controller.allow(
        tenant_id=tenant_id,
        application_id=application_id,
    )
    assert not controller.allow(
        tenant_id=tenant_id,
        application_id=application_id,
    )

    current_time = 159.9

    # The first two requests are still inside the 60-second window.
    assert not controller.allow(
        tenant_id=tenant_id,
        application_id=application_id,
    )

    current_time = 160.0

    # Both original requests have now left the window.
    assert controller.allow(
        tenant_id=tenant_id,
        application_id=application_id,
    )


def test_rejected_rate_limited_request_does_not_consume_future_capacity(
    monkeypatch,
):
    from app.infrastructure import gateway

    current_time = 200.0
    monkeypatch.setattr(
        gateway.time,
        "monotonic",
        lambda: current_time,
    )

    controller = DeveloperRateController(
        limiter=RateLimiter(limit=1, window=60),
    )

    tenant_id = uuid4()
    application_id = uuid4()

    assert controller.allow(
        tenant_id=tenant_id,
        application_id=application_id,
    )

    # This request is rejected and must not create another hit.
    assert not controller.allow(
        tenant_id=tenant_id,
        application_id=application_id,
    )

    current_time = 260.0

    # The original accepted request expired; the rejected request
    # must not affect the next window.
    assert controller.allow(
        tenant_id=tenant_id,
        application_id=application_id,
    )


def test_developer_rate_limit_is_concurrency_safe():
    from concurrent.futures import ThreadPoolExecutor

    controller = DeveloperRateController(
        limiter=RateLimiter(limit=10, window=60),
    )

    tenant_id = uuid4()
    application_id = uuid4()

    def attempt(_index: int) -> bool:
        return controller.allow(
            tenant_id=tenant_id,
            application_id=application_id,
        )

    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(attempt, range(100)))

    assert sum(results) == 10


def test_developer_rate_limit_rejects_conflicting_dependencies():
    with pytest.raises(ValueError):
        DeveloperRateController(
            policy=DeveloperRateLimit(
                limit=10,
                window_seconds=60,
            ),
            limiter=RateLimiter(limit=10, window=60),
        )
