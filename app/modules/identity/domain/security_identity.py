from __future__ import annotations
from dataclasses import dataclass
from uuid import UUID
from app.shared.domain.errors import InvalidDomainData, UnauthorizedDomainAction

@dataclass(frozen=True, slots=True)
class SecurityIdentity:
    user_id: UUID
    authentication_id: UUID
    assurance_level: str = "standard"
    authenticated: bool = True
    def __post_init__(self):
        if not isinstance(self.user_id, UUID) or not isinstance(self.authentication_id, UUID):
            raise InvalidDomainData("security identity ids must be UUID")
        if self.assurance_level not in {"standard", "strong"}:
            raise InvalidDomainData("invalid assurance level")

@dataclass(frozen=True, slots=True)
class ActorContext:
    actor_id: UUID | None
    authentication_id: UUID | None
    correlation_id: UUID
    actor_type: str = "human"
    authenticated: bool = True
    def require_authenticated(self) -> None:
        if not self.authenticated or self.actor_id is None:
            raise UnauthorizedDomainAction("authenticated actor is required")
        if self.actor_type not in {"human", "system", "ai"}:
            raise UnauthorizedDomainAction("invalid actor type")
