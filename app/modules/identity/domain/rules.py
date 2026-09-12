from __future__ import annotations
from dataclasses import dataclass
from app.shared.domain.rules.engine import RuleContext, RuleResult, RuleSet
from .models import User, UserStatus
from .security import CredentialBoundaryContract

@dataclass(frozen=True)
class UserIdentityIntegrityRule:
    code: str = 'identity.user.identity_integrity'
    def check(self, target: User, context: RuleContext) -> RuleResult:
        ok = bool(target.email_address.strip()) and bool(target.name.strip())
        return RuleResult(self.code, 'user identity is valid' if ok else 'user email and display name are required', ok)

@dataclass(frozen=True)
class UserLifecycleStatusRule:
    code: str = 'identity.user.lifecycle_status'
    def check(self, target: User, context: RuleContext) -> RuleResult:
        ok = isinstance(target.status, UserStatus)
        return RuleResult(self.code, 'user lifecycle status is valid' if ok else 'invalid user lifecycle status', ok)

@dataclass(frozen=True)
class UserArchivedTerminalRule:
    code: str = 'identity.user.archived_terminal'
    def check(self, target: User, context: RuleContext) -> RuleResult:
        if target.status is not UserStatus.ARCHIVED:
            return RuleResult(self.code, 'terminal rule not applicable', True)
        forbidden = {'suspend', 'reactivate', 'rename'}
        ok = context.operation not in forbidden
        return RuleResult(self.code, 'archived user is terminal' if ok else 'archived user cannot be mutated by this operation', ok)

@dataclass(frozen=True)
class UserLifecycleTransitionRule:
    code: str = 'identity.user.lifecycle_transition'
    def check(self, target: User, context: RuleContext) -> RuleResult:
        if context.operation is None:
            return RuleResult(self.code, 'no transition requested', True)
        allowed = {'suspend': (UserStatus.ACTIVE,), 'reactivate': (UserStatus.SUSPENDED,), 'archive': (UserStatus.ACTIVE, UserStatus.SUSPENDED)}
        sources = allowed.get(context.operation)
        if sources is None:
            return RuleResult(self.code, 'operation is outside lifecycle transition rules', True)
        ok = target.status in sources
        return RuleResult(self.code, 'lifecycle transition is legal' if ok else f'illegal lifecycle transition for {target.status.value}', ok)

@dataclass(frozen=True)
class UserCredentialBoundaryRule:
    code: str = 'identity.user.credential_boundary'
    def check(self, target: User, context: RuleContext) -> RuleResult:
        try:
            CredentialBoundaryContract.assert_user_boundary(target)
            for event in getattr(target, '_pending_events', ()):
                CredentialBoundaryContract.assert_event_safe(event)
            return RuleResult(self.code, 'credential boundary is clean', True)
        except Exception as exc:
            return RuleResult(self.code, str(exc), False)

USER_RULES = (UserIdentityIntegrityRule(), UserLifecycleStatusRule(), UserArchivedTerminalRule(), UserLifecycleTransitionRule(), UserCredentialBoundaryRule())
USER_RULE_SET = RuleSet(USER_RULES)
