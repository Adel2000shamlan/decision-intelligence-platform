from dataclasses import dataclass
from uuid import uuid4

import pytest

from app.modules.intelligence.context.assembler import DecisionContextAssembler
from app.modules.intelligence.context.models import DecisionContextRequest


@dataclass
class FakeKnowledge:
    items: tuple

    def list(self, tenant_id):
        return self.items


class FakeMemory:
    def __init__(self, items):
        self.items = items

    def list(self, tenant_id, **kwargs):
        return tuple(
            item for item in self.items if item.tenant_id == tenant_id
        )


class FakeGraph:
    def __init__(self, nodes):
        self.nodes_data = nodes

    def nodes(self, tenant_id):
        return tuple(
            item for item in self.nodes_data if item.tenant_id == tenant_id
        )

    def node(self, tenant_id, node_id):
        return next(
            (
                item for item in self.nodes_data
                if item.tenant_id == tenant_id and item.id == node_id
            ),
            None,
        )

    def neighbors(self, tenant_id, node_id):
        return ()


class FakeForecast:
    def observations(self, tenant_id, metric):
        return ()


def test_context_is_tenant_scoped_and_deterministic():
    from app.modules.knowledge.domain.models import KnowledgeItem

    tenant = uuid4()
    other = uuid4()
    decision = uuid4()

    items = (
        KnowledgeItem.create(
            tenant,
            "B",
            "Second",
            "internal",
        ),
        KnowledgeItem.create(
            other,
            "LEAK",
            "Must not appear",
            "other",
        ),
        KnowledgeItem.create(
            tenant,
            "A",
            "First",
            "internal",
        ),
    )

    request = DecisionContextRequest(
        tenant_id=tenant,
        decision_id=decision,
    )

    context = DecisionContextAssembler(
        knowledge=FakeKnowledge(items),
    ).assemble(request)

    assert all(item.tenant_id == tenant for item in context.evidence)
    assert len(context.evidence) == 2
    assert [item.source for item in context.evidence] == ["knowledge", "knowledge"]


def test_context_requires_evidence():
    tenant = uuid4()

    request = DecisionContextRequest(
        tenant_id=tenant,
        decision_id=uuid4(),
    )

    with pytest.raises(ValueError, match="no usable evidence"):
        DecisionContextAssembler().assemble(request)


def test_context_preserves_memory_assumptions():
    from app.modules.memory.domain.models import MemoryItem, MemoryType

    tenant = uuid4()

    memory = MemoryItem.create(
        tenant_id=tenant,
        memory_type=MemoryType.ASSUMPTION,
        content="Demand may increase",
        source="planning",
    )

    request = DecisionContextRequest(
        tenant_id=tenant,
        decision_id=uuid4(),
    )

    context = DecisionContextAssembler(
        memory=FakeMemory((memory,)),
    ).assemble(request)

    assert context.assumptions == ("Demand may increase",)
    assert context.evidence[0].evidence_type.value == "assumption"


def test_context_forecast_observation_is_not_estimate_or_fact():
    from datetime import datetime, timezone
    from app.modules.forecasting.domain.models import ForecastObservation

    tenant = uuid4()

    observation = ForecastObservation.create(
        tenant_id=tenant,
        metric_name="revenue",
        observed_at=datetime.now(timezone.utc),
        value=100.0,
    )

    class Forecast:
        def observations(self, tenant_id, metric):
            return (observation,)

    request = DecisionContextRequest(
        tenant_id=tenant,
        decision_id=uuid4(),
        forecast_metrics=("revenue",),
    )

    context = DecisionContextAssembler(
        forecasting=Forecast(),
    ).assemble(request)

    assert len(context.evidence) == 1
    assert not context.estimates
    assert not context.confirmed_facts
    assert context.evidence[0].evidence_type.value == "observation"


def test_context_request_rejects_non_uuid_graph_ids():
    with pytest.raises(ValueError, match="graph_node_ids"):
        DecisionContextRequest(
            tenant_id=uuid4(),
            decision_id=uuid4(),
            graph_node_ids=("bad",),
        )


def test_context_does_not_promote_knowledge_or_graph_to_confirmed_facts():
    from app.modules.knowledge.domain.models import KnowledgeItem

    tenant = uuid4()
    knowledge = KnowledgeItem.create(
        tenant,
        "Source",
        "Unverified contextual information",
        "internal",
    )

    request = DecisionContextRequest(
        tenant_id=tenant,
        decision_id=uuid4(),
    )

    context = DecisionContextAssembler(
        knowledge=FakeKnowledge((knowledge,)),
    ).assemble(request)

    assert not context.confirmed_facts
    assert context.evidence[0].evidence_type.value == "document"


def test_context_memory_fact_is_confirmed_fact():
    from app.modules.memory.domain.models import MemoryItem, MemoryType

    tenant = uuid4()
    memory = MemoryItem.create(
        tenant_id=tenant,
        memory_type=MemoryType.FACT,
        content="Verified annual revenue is 100000",
        source="verified-record",
    )

    request = DecisionContextRequest(
        tenant_id=tenant,
        decision_id=uuid4(),
    )

    context = DecisionContextAssembler(
        memory=FakeMemory((memory,)),
    ).assemble(request)

    assert context.confirmed_facts == ("Verified annual revenue is 100000",)
    assert context.evidence[0].evidence_type.value == "fact"


def test_context_excludes_risk_without_verified_tenant():
    class RiskWithoutTenant:
        def __init__(self, project_id, decision_id):
            self.id = uuid4()
            self.project_id = project_id
            self.decision_id = decision_id
            self.title = "Unknown tenant risk"

    class RiskSource:
        def list_by_project(self, project_id):
            return (
                RiskWithoutTenant(project_id, decision),
            )

    tenant = uuid4()
    project = uuid4()
    decision = uuid4()

    request = DecisionContextRequest(
        tenant_id=tenant,
        decision_id=decision,
        project_id=project,
    )

    with pytest.raises(ValueError, match="no usable evidence"):
        DecisionContextAssembler(
            risk=RiskSource(),
        ).assemble(request)
