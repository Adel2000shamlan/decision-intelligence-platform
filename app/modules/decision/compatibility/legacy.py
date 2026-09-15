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


from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class LegacyDecisionMigration:
    legacy_id: str
    organization_id: UUID
    project_id: UUID
    title: str
    objective: str
    official_status: DecisionStatus
    version: int | None = None


def build_legacy_migration(
    legacy_id: str,
    organization_id: UUID | None,
    project_id: UUID,
    title: str,
    objective: str,
    status: str | LegacyDecisionStatus,
    version: int | None = None,
) -> LegacyDecisionMigration:
    if organization_id is None:
        raise InvalidDomainData("organization_id is required")

    if not isinstance(project_id, UUID):
        raise InvalidDomainData("project_id must be UUID")

    if not isinstance(title, str) or not title.strip():
        raise InvalidDomainData("title is required")

    if not isinstance(objective, str) or not objective.strip():
        raise InvalidDomainData("objective is required")

    if not isinstance(legacy_id, str) or not legacy_id.strip():
        raise InvalidDomainData("legacy_id is required")

    if version is not None and version < 1:
        raise InvalidDomainData("version must be >= 1")

    return LegacyDecisionMigration(
        legacy_id=legacy_id.strip(),
        organization_id=organization_id,
        project_id=project_id,
        title=title.strip(),
        objective=objective.strip(),
        official_status=to_official_status(status),
        version=version,
    )


def to_create_command(
    migration: LegacyDecisionMigration,
    *,
    description: str | None = None,
    actor_id: UUID | None = None,
):
    from app.modules.decision.application.commands import CreateDecision

    if description is None or not isinstance(description, str) or not description.strip():
        raise InvalidDomainData("explicit official description is required")

    if not isinstance(migration, LegacyDecisionMigration):
        raise InvalidDomainData("migration must be LegacyDecisionMigration")

    if migration.official_status is not DecisionStatus.DRAFT:
        raise InvalidDomainData(
            "only legacy decisions mapped to official draft can be created as new official decisions"
        )

    return CreateDecision(
        organization_id=migration.organization_id,
        project_id=migration.project_id,
        title=migration.title,
        description=description.strip(),
        actor_id=actor_id,
    )
