from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.intelligence.domain.evidence import Evidence


@dataclass(frozen=True, slots=True)
class DecisionContextRequest:
    tenant_id: UUID
    decision_id: UUID
    project_id: UUID | None = None
    knowledge_query: str | None = None
    graph_node_ids: tuple[UUID, ...] = ()
    forecast_metrics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, UUID):
            raise ValueError("tenant_id must be UUID")
        if not isinstance(self.decision_id, UUID):
            raise ValueError("decision_id must be UUID")
        if self.project_id is not None and not isinstance(self.project_id, UUID):
            raise ValueError("project_id must be UUID")
        if self.knowledge_query is not None and (
            not isinstance(self.knowledge_query, str)
            or not self.knowledge_query.strip()
        ):
            raise ValueError("knowledge_query must be non-empty when provided")
        if not isinstance(self.graph_node_ids, tuple):
            raise ValueError("graph_node_ids must be immutable tuple")
        if not all(isinstance(item, UUID) for item in self.graph_node_ids):
            raise ValueError("graph_node_ids must contain UUID values")
        if not isinstance(self.forecast_metrics, tuple):
            raise ValueError("forecast_metrics must be immutable tuple")
        if not all(
            isinstance(item, str) and item.strip()
            for item in self.forecast_metrics
        ):
            raise ValueError("forecast_metrics must contain non-empty strings")


@dataclass(frozen=True, slots=True)
class DecisionContext:
    tenant_id: UUID
    decision_id: UUID
    project_id: UUID | None
    evidence: tuple[Evidence, ...]
    confirmed_facts: tuple[str, ...]
    assumptions: tuple[str, ...]
    estimates: tuple[str, ...]
    sources: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, UUID):
            raise ValueError("tenant_id must be UUID")
        if not isinstance(self.decision_id, UUID):
            raise ValueError("decision_id must be UUID")
        if self.project_id is not None and not isinstance(self.project_id, UUID):
            raise ValueError("project_id must be UUID")
        if not isinstance(self.evidence, tuple) or not self.evidence:
            raise ValueError("context requires at least one evidence item")
        if not all(isinstance(item, Evidence) for item in self.evidence):
            raise ValueError("evidence must contain Evidence items")

        for name in (
            "confirmed_facts",
            "assumptions",
            "estimates",
            "sources",
        ):
            if not isinstance(getattr(self, name), tuple):
                raise ValueError(f"{name} must be immutable tuple")
