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


class LegacyMigrationDisposition(str, Enum):
    MIGRATABLE = "migratable"
    REQUIRES_EXISTING_MIGRATION = "requires_existing_migration"
    BLOCKED = "blocked"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class LegacyMigrationPolicyResult:
    disposition: LegacyMigrationDisposition
    official_status: DecisionStatus | None
    reason: str


def evaluate_migration_policy(
    status: str | LegacyDecisionStatus,
    organization_id: UUID | None,
) -> LegacyMigrationPolicyResult:
    if organization_id is None:
        return LegacyMigrationPolicyResult(
            disposition=LegacyMigrationDisposition.BLOCKED,
            official_status=None,
            reason="organization_id is required for migration",
        )

    if not isinstance(organization_id, UUID):
        return LegacyMigrationPolicyResult(
            disposition=LegacyMigrationDisposition.BLOCKED,
            official_status=None,
            reason="organization_id must be UUID",
        )

    try:
        official_status = to_official_status(status)
    except InvalidDomainData as exc:
        if str(status) == LegacyDecisionStatus.ARCHIVED.value:
            return LegacyMigrationPolicyResult(
                disposition=LegacyMigrationDisposition.UNSUPPORTED,
                official_status=None,
                reason=str(exc),
            )
        raise

    if official_status is DecisionStatus.DRAFT:
        return LegacyMigrationPolicyResult(
            disposition=LegacyMigrationDisposition.MIGRATABLE,
            official_status=official_status,
            reason="legacy draft can be created as a new official decision",
        )

    return LegacyMigrationPolicyResult(
        disposition=LegacyMigrationDisposition.REQUIRES_EXISTING_MIGRATION,
        official_status=official_status,
        reason="legacy decision requires an existing official decision before state migration",
    )


@dataclass(frozen=True)
class LegacyMigrationPlan:
    legacy_id: str
    disposition: LegacyMigrationDisposition
    action: str
    official_status: DecisionStatus | None
    reason: str


def build_migration_plan(
    legacy_id: str,
    status: str | LegacyDecisionStatus,
    organization_id: UUID | None,
) -> LegacyMigrationPlan:
    if not isinstance(legacy_id, str) or not legacy_id.strip():
        raise ValueError("legacy_id is required")

    policy = evaluate_migration_policy(
        status=status,
        organization_id=organization_id,
    )

    if policy.disposition is LegacyMigrationDisposition.MIGRATABLE:
        action = "create_official_decision"
    elif (
        policy.disposition
        is LegacyMigrationDisposition.REQUIRES_EXISTING_MIGRATION
    ):
        action = "link_existing_official_decision"
    elif policy.disposition is LegacyMigrationDisposition.UNSUPPORTED:
        action = "reject_migration"
    else:
        action = "block_migration"

    return LegacyMigrationPlan(
        legacy_id=legacy_id.strip(),
        disposition=policy.disposition,
        action=action,
        official_status=policy.official_status,
        reason=policy.reason,
    )


@dataclass(frozen=True)
class LegacyMigrationInput:
    legacy_id: str
    organization_id: UUID
    project_id: UUID
    title: str
    objective: str
    official_status: DecisionStatus


def validate_migration_input(
    legacy_id: str,
    organization_id: UUID | None,
    project_id: UUID | None,
    title: str,
    objective: str,
    status: str | LegacyDecisionStatus,
) -> LegacyMigrationInput:
    if not isinstance(legacy_id, str) or not legacy_id.strip():
        raise InvalidDomainData("legacy_id is required")

    if organization_id is None:
        raise InvalidDomainData("organization_id is required")

    if not isinstance(organization_id, UUID):
        raise InvalidDomainData("organization_id must be UUID")

    if project_id is None:
        raise InvalidDomainData("project_id is required")

    if not isinstance(project_id, UUID):
        raise InvalidDomainData("project_id must be UUID")

    if not isinstance(title, str) or not title.strip():
        raise InvalidDomainData("title is required")

    if not isinstance(objective, str) or not objective.strip():
        raise InvalidDomainData("objective is required")

    if str(status) == LegacyDecisionStatus.ARCHIVED.value:
        raise InvalidDomainData(
            "legacy decision status 'archived' is unsupported"
        )

    official_status = to_official_status(status)

    return LegacyMigrationInput(
        legacy_id=legacy_id.strip(),
        organization_id=organization_id,
        project_id=project_id,
        title=title.strip(),
        objective=objective.strip(),
        official_status=official_status,
    )


@dataclass(frozen=True)
class LegacyMigrationLink:
    legacy_id: str
    official_id: UUID
    official_status: DecisionStatus


def build_migration_link(
    legacy_id: str,
    official_id: UUID | None,
    legacy_status: str | LegacyDecisionStatus,
) -> LegacyMigrationLink:
    if not isinstance(legacy_id, str) or not legacy_id.strip():
        raise InvalidDomainData("legacy_id is required")

    if official_id is None:
        raise InvalidDomainData("official_id is required")

    if not isinstance(official_id, UUID):
        raise InvalidDomainData("official_id must be UUID")

    try:
        legacy_status_value = LegacyDecisionStatus(legacy_status)
    except (ValueError, TypeError) as exc:
        raise InvalidDomainData(
            f"unsupported legacy decision status: {legacy_status!r}"
        ) from exc

    if legacy_status_value is LegacyDecisionStatus.ARCHIVED:
        raise InvalidDomainData(
            "legacy decision status 'archived' cannot be linked"
        )

    if legacy_status_value is LegacyDecisionStatus.DRAFT:
        raise InvalidDomainData(
            "legacy draft requires create path, not existing-decision link"
        )

    return LegacyMigrationLink(
        legacy_id=legacy_id.strip(),
        official_id=official_id,
        official_status=to_official_status(legacy_status_value),
    )


def validate_migration_consistency(
    legacy_status: str | LegacyDecisionStatus,
    official_status: DecisionStatus | None,
) -> bool:
    if official_status is None:
        raise InvalidDomainData("official_status is required")

    if not isinstance(official_status, DecisionStatus):
        raise InvalidDomainData("official_status must be DecisionStatus")

    try:
        legacy_status_value = LegacyDecisionStatus(legacy_status)
    except (ValueError, TypeError) as exc:
        raise InvalidDomainData(
            f"unsupported legacy decision status: {legacy_status!r}"
        ) from exc

    if legacy_status_value is LegacyDecisionStatus.ARCHIVED:
        raise InvalidDomainData(
            "legacy decision status 'archived' is unsupported"
        )

    expected_status = to_official_status(legacy_status_value)

    if expected_status is not official_status:
        raise InvalidDomainData(
            "status mismatch between legacy and official decision"
        )

    return True
