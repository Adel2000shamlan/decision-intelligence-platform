from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class AgentCapability(str, Enum):
    RESEARCH = "research"
    MARKET = "market"
    FINANCE = "finance"
    RISK = "risk"
    SCENARIO = "scenario"
    DECISION = "decision"
    EXECUTION = "execution"
    KPI = "kpi"
    REPORTING = "reporting"


class AgentExecutionStatus(str, Enum):
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    FAILED = "failed"
    DENIED = "denied"


@dataclass(frozen=True, slots=True)
class AgentTask:
    task_id: UUID
    tenant_id: UUID
    agent_id: UUID
    capability: AgentCapability
    objective: str
    correlation_id: UUID

    def __post_init__(self) -> None:
        for name in (
            "task_id",
            "tenant_id",
            "agent_id",
            "correlation_id",
        ):
            if not isinstance(getattr(self, name), UUID):
                raise ValueError(f"{name} must be UUID")

        object.__setattr__(
            self,
            "capability",
            AgentCapability(self.capability),
        )

        if not isinstance(self.objective, str) or not self.objective.strip():
            raise ValueError("objective is required")

        object.__setattr__(self, "objective", self.objective.strip())


@dataclass(frozen=True, slots=True)
class AgentTool:
    name: str
    capability: AgentCapability
    description: str
    approved: bool = False

    def __post_init__(self) -> None:
        for name in ("name", "description"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")

        object.__setattr__(
            self,
            "name",
            self.name.strip(),
        )
        object.__setattr__(
            self,
            "description",
            self.description.strip(),
        )
        object.__setattr__(
            self,
            "capability",
            AgentCapability(self.capability),
        )

        if not isinstance(self.approved, bool):
            raise ValueError("approved must be bool")


@dataclass(frozen=True, slots=True)
class AgentExecutionResult:
    task_id: UUID
    agent_id: UUID
    status: AgentExecutionStatus
    output: object
    evidence_ids: tuple[UUID, ...] = ()

    def __post_init__(self) -> None:
        for name in ("task_id", "agent_id"):
            if not isinstance(getattr(self, name), UUID):
                raise ValueError(f"{name} must be UUID")

        object.__setattr__(
            self,
            "status",
            AgentExecutionStatus(self.status),
        )

        if not isinstance(self.evidence_ids, tuple):
            raise ValueError("evidence_ids must be immutable tuple")

        if not all(isinstance(item, UUID) for item in self.evidence_ids):
            raise ValueError("evidence_ids must contain UUID values")
