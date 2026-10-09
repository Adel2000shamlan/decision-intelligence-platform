from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any
from uuid import UUID, uuid5, NAMESPACE_URL

from app.modules.intelligence.domain.evidence import Evidence, EvidenceType

from .models import DecisionContext, DecisionContextRequest


class DecisionContextAssembler:
    """
    Builds a tenant-scoped, deterministic decision context.

    The assembler collects existing domain information but never:
    - approves or rejects a decision;
    - executes a decision;
    - invents scoring factors;
    - promotes forecasts or assumptions to confirmed facts.
    """

    def __init__(
        self,
        *,
        knowledge=None,
        knowledge_graph=None,
        memory=None,
        risk=None,
        scenario=None,
        forecasting=None,
    ) -> None:
        self.knowledge = knowledge
        self.knowledge_graph = knowledge_graph
        self.memory = memory
        self.risk = risk
        self.scenario = scenario
        self.forecasting = forecasting

    def assemble(self, request: DecisionContextRequest) -> DecisionContext:
        evidence: list[Evidence] = []
        confirmed: list[str] = []
        assumptions: list[str] = []
        estimates: list[str] = []
        sources: list[str] = []

        self._knowledge(request, evidence, confirmed, sources)
        self._graph(request, evidence, confirmed, sources)
        self._memory(request, evidence, confirmed, assumptions, sources)
        self._risk(request, evidence, confirmed, assumptions, sources)
        self._scenario(request, evidence, estimates, sources)
        self._forecast(request, evidence, estimates, sources)

        evidence = self._deduplicate_and_sort(evidence)

        if not evidence:
            raise ValueError("decision context contains no usable evidence")

        for item in evidence:
            if item.tenant_id != request.tenant_id:
                raise ValueError("context evidence tenant mismatch")

        return DecisionContext(
            tenant_id=request.tenant_id,
            decision_id=request.decision_id,
            project_id=request.project_id,
            evidence=tuple(evidence),
            confirmed_facts=self._unique_sorted(confirmed),
            assumptions=self._unique_sorted(assumptions),
            estimates=self._unique_sorted(estimates),
            sources=self._unique_sorted(sources),
        )

    def _knowledge(self, request, evidence, confirmed, sources) -> None:
        if self.knowledge is None:
            return

        items = (
            self.knowledge.search(request.tenant_id, request.knowledge_query)
            if request.knowledge_query is not None
            and hasattr(self.knowledge, "search")
            else self.knowledge.list(request.tenant_id)
            if hasattr(self.knowledge, "list")
            else ()
        )

        for item in items:
            if item.tenant_id != request.tenant_id:
                continue
            if request.project_id is not None and item.project_id not in (
                None,
                request.project_id,
            ):
                continue

            reference = str(item.evidence_uri or item.id)
            ev = self._evidence(
                request.tenant_id,
                "knowledge",
                reference,
                f"{item.title}: {item.content}",
                EvidenceType.DOCUMENT,
            )
            evidence.append(ev)
            sources.append(item.source)

    def _graph(self, request, evidence, confirmed, sources) -> None:
        if self.knowledge_graph is None:
            return

        graph = self.knowledge_graph
        nodes = []

        if request.graph_node_ids:
            for node_id in request.graph_node_ids:
                node = graph.node(request.tenant_id, node_id)
                if node is not None:
                    nodes.append(node)
                    nodes.extend(graph.neighbors(request.tenant_id, node_id))
        else:
            # Knowledge Graph has no canonical decision_id field on nodes.
            # Context must therefore use only explicitly supplied node IDs.
            nodes = []

        seen: set[UUID] = set()
        for node in nodes:
            if node.id in seen or node.tenant_id != request.tenant_id:
                continue
            seen.add(node.id)

            statement = f"{node.node_type.value}: {node.label}"
            evidence.append(
                self._evidence(
                    request.tenant_id,
                    "knowledge-graph",
                    str(node.id),
                    statement,
                    EvidenceType.SOURCE,
                )
            )
            sources.append(node.source)

    def _memory(
        self, request, evidence, confirmed, assumptions, sources
    ) -> None:
        if self.memory is None:
            return

        items = self.memory.list(request.tenant_id)
        for item in items:
            if item.tenant_id != request.tenant_id:
                continue
            if getattr(item.status, "value", item.status) != "active":
                continue

            statement = item.content
            memory_type = getattr(item.memory_type, "value", item.memory_type)
            if memory_type == "assumption":
                evidence_type = EvidenceType.ASSUMPTION
            elif memory_type == "fact":
                evidence_type = EvidenceType.FACT
            else:
                evidence_type = EvidenceType.OBSERVATION

            evidence.append(
                self._evidence(
                    request.tenant_id,
                    "memory",
                    str(item.id),
                    statement,
                    evidence_type,
                )
            )

            if evidence_type is EvidenceType.ASSUMPTION:
                assumptions.append(statement)
            elif evidence_type is EvidenceType.FACT:
                confirmed.append(statement)

            sources.append(item.source)

    def _risk(
        self, request, evidence, confirmed, assumptions, sources
    ) -> None:
        if self.risk is None or request.project_id is None:
            return

        items = self.risk.list_by_project(request.project_id)
        for item in items:
            item_tenant = getattr(item, "tenant_id", None)
            if item_tenant is None or item_tenant != request.tenant_id:
                continue

            decision_id = getattr(item, "decision_id", None)
            if decision_id is not None and decision_id != request.decision_id:
                continue

            statement = self._safe_text(item)
            evidence.append(
                self._evidence(
                    request.tenant_id,
                    "risk",
                    str(getattr(item, "id", request.decision_id)),
                    statement,
                    EvidenceType.OBSERVATION,
                )
            )
            sources.append("risk")

    def _scenario(self, request, evidence, estimates, sources) -> None:
        if self.scenario is None:
            return

        items = self.scenario.list_by_decision(request.decision_id)
        for item in items:
            statement = self._safe_text(item)
            evidence.append(
                self._evidence(
                    request.tenant_id,
                    "scenario",
                    str(getattr(item, "id", request.decision_id)),
                    statement,
                    EvidenceType.OBSERVATION,
                )
            )
            sources.append("scenario")

    def _forecast(self, request, evidence, estimates, sources) -> None:
        if self.forecasting is None:
            return

        for metric in request.forecast_metrics:
            observations = self.forecasting.observations(
                request.tenant_id, metric
            )
            for observation in observations:
                statement = (
                    f"{metric} observed value={observation.value} "
                    f"at {observation.observed_at.isoformat()}"
                )
                evidence.append(
                    self._evidence(
                        request.tenant_id,
                        "forecasting",
                        f"{metric}:{observation.observed_at.isoformat()}",
                        statement,
                        EvidenceType.OBSERVATION,
                    )
                )
                sources.append("forecasting")

    @staticmethod
    def _evidence(
        tenant_id: UUID,
        source: str,
        reference: str,
        statement: str,
        evidence_type: EvidenceType,
    ) -> Evidence:
        evidence_id = uuid5(
            NAMESPACE_URL,
            f"decision-context:{tenant_id}:{source}:{reference}",
        )
        return Evidence(
            evidence_id=evidence_id,
            tenant_id=tenant_id,
            evidence_type=evidence_type,
            source=source,
            reference=reference,
            statement=statement,
            traceable=True,
        )

    @staticmethod
    def _deduplicate_and_sort(items: list[Evidence]) -> list[Evidence]:
        unique = {item.evidence_id: item for item in items}
        return sorted(
            unique.values(),
            key=lambda item: (
                item.source,
                item.reference,
                str(item.evidence_id),
            ),
        )

    @staticmethod
    def _unique_sorted(items: list[str]) -> tuple[str, ...]:
        return tuple(sorted(set(item for item in items if item)))

    @staticmethod
    def _safe_text(item: Any) -> str:
        if is_dataclass(item):
            values = asdict(item)
            return "; ".join(
                f"{key}={DecisionContextAssembler._stringify(value)}"
                for key, value in sorted(values.items())
                if key not in {"created_at", "updated_at"}
            )

        return str(item)

    @staticmethod
    def _stringify(value: Any) -> str:
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, (tuple, list)):
            return ", ".join(
                DecisionContextAssembler._stringify(item) for item in value
            )
        return str(value)
