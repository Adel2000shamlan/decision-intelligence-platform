from uuid import uuid4

from app.modules.agent.application.orchestrator import AgentOrchestrator
from app.modules.agent.domain.evidence import AgentEvidenceSet
from app.modules.agent.domain.execution import (
    AgentCapability,
    AgentTask,
    AgentTool,
)
from app.modules.agent.domain.models import Agent
from app.modules.agent.domain.tool_registry import AgentToolRegistry
from app.modules.intelligence.domain.evidence import Evidence, EvidenceType


def make_evidence(tenant_id):
    return Evidence(
        evidence_id=uuid4(),
        tenant_id=tenant_id,
        evidence_type=EvidenceType.SOURCE,
        source="test-source",
        reference="test-reference",
        statement="Verified execution evidence.",
        traceable=True,
    )


def build_context():
    tenant_id = uuid4()
    agent = Agent.register(
        tenant_id=tenant_id,
        name="Evidence Agent",
        capabilities=(AgentCapability.RESEARCH.value,),
    )
    task = AgentTask(
        task_id=uuid4(),
        tenant_id=tenant_id,
        agent_id=agent.id,
        capability=AgentCapability.RESEARCH,
        objective="Collect verified evidence.",
        correlation_id=uuid4(),
    )
    tool = AgentTool(
        name="research-tool",
        capability=AgentCapability.RESEARCH,
        description="Collect research evidence.",
        approved=True,
    )
    evidence = AgentEvidenceSet(
        tenant_id=tenant_id,
        evidence=(make_evidence(tenant_id),),
    )
    registry = AgentToolRegistry()
    registry.register(tool)
    orchestrator = AgentOrchestrator(registry)

    return agent, task, evidence, orchestrator


def test_orchestrator_attaches_evidence_ids_to_completed_execution():
    agent, task, evidence, orchestrator = build_context()

    receipt = orchestrator.execute(
        agent,
        task,
        "research-tool",
        lambda _: {"finding": "verified"},
        evidence=evidence,
    )

    assert receipt.result.status.value == "completed"
    assert receipt.result.evidence_ids == evidence.evidence_ids


def test_orchestrator_rejects_completed_execution_without_required_evidence():
    agent, task, _, orchestrator = build_context()

    receipt = orchestrator.execute(
        agent,
        task,
        "research-tool",
        lambda _: {"finding": "unsupported"},
    )

    assert receipt.result.status.value == "denied"
    assert receipt.result.output["reason"] == "execution evidence is required"


def test_orchestrator_rejects_cross_tenant_evidence_before_handler():
    agent, task, _, orchestrator = build_context()
    other_tenant = uuid4()

    evidence = AgentEvidenceSet(
        tenant_id=other_tenant,
        evidence=(make_evidence(other_tenant),),
    )

    called = False

    def handler(_):
        nonlocal called
        called = True
        return {"finding": "should not execute"}

    receipt = orchestrator.execute(
        agent,
        task,
        "research-tool",
        handler,
        evidence=evidence,
    )

    assert receipt.result.status.value == "denied"
    assert called is False
    assert receipt.result.output["reason"] == "evidence tenant mismatch"
