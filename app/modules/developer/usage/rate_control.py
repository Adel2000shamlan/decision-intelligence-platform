from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.infrastructure.gateway import RateLimiter


@dataclass(frozen=True, slots=True)
class DeveloperRateLimit:
    """Explicit request-rate policy for one Developer Application."""

    limit: int
    window_seconds: int

    def __post_init__(self) -> None:
        if not isinstance(self.limit, int) or isinstance(self.limit, bool):
            raise ValueError("limit must be an integer")
        if self.limit <= 0:
            raise ValueError("limit must be greater than zero")

        if not isinstance(self.window_seconds, int) or isinstance(
            self.window_seconds, bool
        ):
            raise ValueError("window_seconds must be an integer")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be greater than zero")


class DeveloperRateController:
    """
    Application-scoped request-rate control.

    The existing thread-safe RateLimiter remains the underlying primitive.
    A composite tenant/application key prevents cross-tenant and
    cross-application bucket sharing.
    """

    def __init__(
        self,
        *,
        policy: DeveloperRateLimit | None = None,
        limiter: RateLimiter | None = None,
    ) -> None:
        if policy is not None and limiter is not None:
            raise ValueError("provide either policy or limiter, not both")

        if limiter is not None:
            self.limiter = limiter
        else:
            resolved_policy = policy or DeveloperRateLimit(
                limit=60,
                window_seconds=60,
            )
            self.limiter = RateLimiter(
                limit=resolved_policy.limit,
                window=resolved_policy.window_seconds,
            )

    @staticmethod
    def _key(
        *,
        tenant_id: UUID,
        application_id: UUID,
    ) -> str:
        if not isinstance(tenant_id, UUID):
            raise ValueError("tenant_id must be a UUID")
        if not isinstance(application_id, UUID):
            raise ValueError("application_id must be a UUID")

        return f"developer:{tenant_id}:{application_id}"

    def allow(
        self,
        *,
        tenant_id: UUID,
        application_id: UUID,
    ) -> bool:
        key = self._key(
            tenant_id=tenant_id,
            application_id=application_id,
        )
        return self.limiter.allow(key)
