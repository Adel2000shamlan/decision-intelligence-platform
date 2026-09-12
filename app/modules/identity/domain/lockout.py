from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from app.shared.domain.errors import BusinessRuleViolation, InvalidDomainData

@dataclass(frozen=True, slots=True)
class AuthenticationFailureState:
    user_id: UUID
    failed_attempts: int = 0
    locked_until: datetime | None = None
    lock_count: int = 0
    version: int = 1
    def __post_init__(self):
        if self.failed_attempts < 0 or self.lock_count < 0 or self.version < 1: raise InvalidDomainData("invalid failure state")

@dataclass(frozen=True, slots=True)
class LockoutPolicy:
    max_failures: int = 5
    lockout_seconds: int = 300
    def __post_init__(self):
        if self.max_failures < 1 or self.lockout_seconds < 1: raise InvalidDomainData("invalid lockout policy")

class AuthenticationFailureService:
    def __init__(self, policy: LockoutPolicy | None = None): self.policy = policy or LockoutPolicy()
    def record_failure(self, state: AuthenticationFailureState, now: datetime | None = None) -> AuthenticationFailureState:
        now = now or datetime.now(timezone.utc)
        if state.locked_until and state.locked_until > now: return state
        attempts = state.failed_attempts + 1
        if attempts >= self.policy.max_failures:
            return AuthenticationFailureState(state.user_id, 0, now + timedelta(seconds=self.policy.lockout_seconds), state.lock_count + 1, state.version + 1)
        return AuthenticationFailureState(state.user_id, attempts, None, state.lock_count, state.version + 1)
    def record_success(self, state: AuthenticationFailureState, now: datetime | None = None) -> AuthenticationFailureState:
        now = now or datetime.now(timezone.utc)
        if state.locked_until and state.locked_until > now: raise BusinessRuleViolation("authentication is temporarily locked")
        return AuthenticationFailureState(state.user_id, 0, None, state.lock_count, state.version + 1)
    def assert_allowed(self, state: AuthenticationFailureState, now: datetime | None = None) -> None:
        now = now or datetime.now(timezone.utc)
        if state.locked_until and state.locked_until > now: raise BusinessRuleViolation("authentication is temporarily locked")
