from __future__ import annotations

from enum import Enum

from app.modules.decision.domain.models import DecisionStatus
from app.shared.domain.errors import InvalidDomainData


class LegacyDecisionStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


_LEGACY_TO_OFFICIAL = {
    LegacyDecisionStatus.DRAFT: DecisionStatus.DRAFT,
    LegacyDecisionStatus.VALIDATED: DecisionStatus.ANALYSIS,
    LegacyDecisionStatus.SUBMITTED: DecisionStatus.READY_FOR_APPROVAL,
    LegacyDecisionStatus.APPROVED: DecisionStatus.APPROVED,
    LegacyDecisionStatus.REJECTED: DecisionStatus.REJECTED,
    LegacyDecisionStatus.CANCELLED: DecisionStatus.CANCELLED,
    LegacyDecisionStatus.ACTIVE: DecisionStatus.EXECUTED,
    LegacyDecisionStatus.COMPLETED: DecisionStatus.CLOSED,
}


def to_official_status(status: str | LegacyDecisionStatus) -> DecisionStatus:
    try:
        legacy_status = LegacyDecisionStatus(status)
    except (ValueError, TypeError) as exc:
        raise InvalidDomainData(
            f"unsupported legacy decision status: {status!r}"
        ) from exc

    try:
        return _LEGACY_TO_OFFICIAL[legacy_status]
    except KeyError as exc:
        raise InvalidDomainData(
            "legacy decision status 'archived' has no official Decision equivalent"
        ) from exc


def can_migrate_status(status: str | LegacyDecisionStatus) -> bool:
    try:
        to_official_status(status)
    except InvalidDomainData:
        return False
    return True
