from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.errors import EntityNotFound, BusinessRuleViolation
from .ports import RiskUnitOfWork
from ..domain.models import RiskSource
from ..domain.services import RiskDomainService


@dataclass(frozen=True)
class CreateRisk:
    project_id: UUID
    title: str
    description: str = ""
    decision_id: UUID | None = None
    source: RiskSource = RiskSource.HUMAN
    actor_id: UUID | None = None


@dataclass(frozen=True)
class IdentifyRisk:
    risk_id: UUID
    actor_id: UUID | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class AssessRisk:
    risk_id: UUID
    probability: int
    impact: int
    actor_id: UUID | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class StartRiskMitigation:
    risk_id: UUID
    actor_id: UUID | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class MonitorRisk:
    risk_id: UUID
    residual_probability: int
    residual_impact: int
    actor_id: UUID | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class AcceptRisk:
    risk_id: UUID
    actor_id: UUID | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class CloseRisk:
    risk_id: UUID
    actor_id: UUID | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class ArchiveRisk:
    risk_id: UUID
    actor_id: UUID | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class RenameRisk:
    risk_id: UUID
    title: str
    actor_id: UUID | None = None
    expected_version: int | None = None


class RiskCommandHandler:
    def __init__(self, uow: RiskUnitOfWork):
        self.uow = uow
        self.domain = RiskDomainService()

    def create(self, c):
        r = self.uow.factory.create(
            c.project_id,
            c.title,
            c.description,
            c.decision_id,
            c.source,
            c.actor_id,
        )
        self.uow.policy.ensure_unique_title(self.uow.repository, r)
        self.uow.repository.save(r)
        self.uow.commit()
        return r

    def _get(self, i):
        r = self.uow.repository.get_by_id(i)
        if r is None:
            raise EntityNotFound(f"risk not found: {i}")
        return r

    def identify(self, c):
        result = self.domain.identify(
            self.uow.repository,
            c.risk_id,
            c.actor_id,
            c.expected_version,
        )
        self.uow.commit()
        return result.entity

    def assess(self, c):
        self.uow.policy.ensure_can_assess(self._get(c.risk_id))
        result = self.domain.assess(
            self.uow.repository,
            c.risk_id,
            c.probability,
            c.impact,
            c.actor_id,
            c.expected_version,
        )
        self.uow.commit()
        return result.entity

    def start_mitigation(self, c):
        self.uow.policy.ensure_can_select_mitigation(self._get(c.risk_id))
        result = self.domain.start_mitigation(
            self.uow.repository,
            c.risk_id,
            c.actor_id,
            c.expected_version,
        )
        self.uow.commit()
        return result.entity

    def monitor(self, c):
        result = self.domain.monitor(
            self.uow.repository,
            c.risk_id,
            c.residual_probability,
            c.residual_impact,
            c.actor_id,
            c.expected_version,
        )
        self.uow.commit()
        return result.entity

    def accept(self, c):
        result = self.domain.accept(
            self.uow.repository,
            c.risk_id,
            c.actor_id,
            c.expected_version,
        )
        self.uow.commit()
        return result.entity

    def close(self, c):
        result = self.domain.close(
            self.uow.repository,
            c.risk_id,
            c.actor_id,
            c.expected_version,
        )
        self.uow.commit()
        return result.entity

    def archive(self, c):
        result = self.domain.archive(
            self.uow.repository,
            c.risk_id,
            c.actor_id,
            c.expected_version,
        )
        self.uow.commit()
        return result.entity

    def rename(self, c):
        result = self.domain.rename(
            self.uow.repository,
            c.risk_id,
            c.title,
            c.actor_id,
            c.expected_version,
        )
        self.uow.commit()
        return result.entity
