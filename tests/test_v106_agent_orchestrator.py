from uuid import uuid4

from app.modules.agent.domain.evidence import AgentEvidenceSet
from app.modules.intelligence.domain.evidence import Evidence, EvidenceType

from app.modules.agent.application.orchestrator import AgentOrchestrator
from app.modules.agent.domain.execution import (
    AgentCapability,
    AgentExecutionStatus,
    AgentTask,
    AgentTool,
)
from app.modules.agent.domain.models import Agent
from app.modules.agent.domain.tool_registry import AgentToolRegistry


def build_context():
    tenant_id = uuid4()

    agent = Agent.register(
        tenant_id=tenant_id,
        name="research-agent",
        capabilities={AgentCapability.RESEARCH.value},
    )

    task = AgentTask(
        task_id=uuid4(),
        tenant_id=tenant_id,
        agent_id=agent.id,
        capability=AgentCapability.RESEARCH,
        objective="Research the market.",
        correlation_id=uuid4(),
    )

    tool = AgentTool(
        name="research-reader",
        capability=AgentCapability.RESEARCH,
        description="Read approved research sources.",
        approved=True,
    )

    registry = AgentToolRegistry()
    registry.register(tool)

    evidence = AgentEvidenceSet(
        tenant_id=tenant_id,
        evidence=(
            Evidence(
                evidence_id=uuid4(),
                tenant_id=tenant_id,
                evidence_type=EvidenceType.SOURCE,
                source="test-source",
                reference="test-reference",
                statement="Verified test evidence.",
                traceable=True,
            ),
        ),
    )

    return agent, task, registry, evidence


def test_orchestrator_completes_authorized_execution():
    agent, task, registry, evidence = build_context()
    called = []

    def handler(received_task):
        called.append(received_task.task_id)
        return {"status": "ok"}

    receipt = AgentOrchestrator(registry).execute(
        agent,
        task,
        "research-reader",
        handler,
        evidence=evidence,
    )

    assert receipt.result.status is AgentExecutionStatus.COMPLETED
    assert receipt.result.output == {"status": "ok"}
    assert called == [task.task_id]


def test_orchestrator_denies_unregistered_tool_without_calling_handler():
    agent, task, registry, _ = build_context()
    called = []

    def handler(received_task):
        called.append(received_task.task_id)
        return {"status": "should-not-run"}

    receipt = AgentOrchestrator(registry).execute(
        agent,
        task,
        "missing-tool",
        handler,
    )

    assert receipt.result.status is AgentExecutionStatus.DENIED
    assert receipt.result.output == {"reason": "tool not registered"}
    assert called == []


def test_orchestrator_denies_unapproved_tool_without_calling_handler():
    agent, task, registry, _ = build_context()

    registry = AgentToolRegistry()
    registry.register(
        AgentTool(
            name="research-reader",
            capability=AgentCapability.RESEARCH,
            description="Read approved research sources.",
            approved=False,
        )
    )

    called = []

    def handler(received_task):
        called.append(received_task.task_id)
        return {"status": "should-not-run"}

    receipt = AgentOrchestrator(registry).execute(
        agent,
        task,
        "research-reader",
        handler,
    )

    assert receipt.result.status is AgentExecutionStatus.DENIED
    assert receipt.result.output == {"reason": "tool is not approved"}
    assert called == []


def test_orchestrator_returns_failed_result_when_handler_fails():
    agent, task, registry, evidence = build_context()

    def handler(received_task):
        raise RuntimeError("controlled failure")

    receipt = AgentOrchestrator(registry).execute(
        agent,
        task,
        "research-reader",
        handler,
        evidence=evidence,
    )

    assert receipt.result.status is AgentExecutionStatus.FAILED
    assert receipt.result.output["reason"] == "execution failed"
    assert receipt.result.output["error"] == "controlled failure"
