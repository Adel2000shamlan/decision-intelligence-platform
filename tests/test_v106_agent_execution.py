from uuid import uuid4

from app.modules.agent.domain.execution import (
    AgentCapability,
    AgentTask,
    AgentTool,
)
from app.modules.agent.domain.models import Agent
from app.modules.agent.domain.policy import AgentExecutionPolicy


def build_context(capability=AgentCapability.RESEARCH):
    tenant_id = uuid4()
    agent = Agent.register(
        tenant_id=tenant_id,
        name="research-agent",
        capabilities={capability.value},
    )

    task = AgentTask(
        task_id=uuid4(),
        tenant_id=tenant_id,
        agent_id=agent.id,
        capability=capability,
        objective="Research the market.",
        correlation_id=uuid4(),
    )

    tool = AgentTool(
        name="research-reader",
        capability=capability,
        description="Read approved research sources.",
        approved=True,
    )

    return agent, task, tool


def test_agent_execution_policy_allows_valid_task_and_tool():
    agent, task, tool = build_context()

    decision = AgentExecutionPolicy().authorize(agent, task, tool)

    assert decision.allowed is True
    assert decision.policy_id == "agent.execution-boundary.v1"


def test_agent_execution_policy_denies_disabled_agent():
    agent, task, tool = build_context()
    agent = agent.disable()

    decision = AgentExecutionPolicy().authorize(agent, task, tool)

    assert decision.allowed is False
    assert decision.reason == "agent is disabled"


def test_agent_execution_policy_denies_tenant_mismatch():
    agent, task, tool = build_context()
    task = AgentTask(
        task_id=task.task_id,
        tenant_id=uuid4(),
        agent_id=task.agent_id,
        capability=task.capability,
        objective=task.objective,
        correlation_id=task.correlation_id,
    )

    decision = AgentExecutionPolicy().authorize(agent, task, tool)

    assert decision.allowed is False
    assert decision.reason == "agent tenant mismatch"


def test_agent_execution_policy_denies_agent_mismatch():
    agent, task, tool = build_context()
    task = AgentTask(
        task_id=task.task_id,
        tenant_id=task.tenant_id,
        agent_id=uuid4(),
        capability=task.capability,
        objective=task.objective,
        correlation_id=task.correlation_id,
    )

    decision = AgentExecutionPolicy().authorize(agent, task, tool)

    assert decision.allowed is False
    assert decision.reason == "task agent mismatch"


def test_agent_execution_policy_denies_unregistered_capability():
    agent, task, tool = build_context(AgentCapability.MARKET)

    agent = agent.with_capabilities(())

    decision = AgentExecutionPolicy().authorize(agent, task, tool)

    assert decision.allowed is False
    assert decision.reason == "agent capability is not registered"


def test_agent_execution_policy_denies_tool_capability_mismatch():
    agent, task, tool = build_context(AgentCapability.RESEARCH)

    tool = AgentTool(
        name="finance-tool",
        capability=AgentCapability.FINANCE,
        description="Finance analysis tool.",
        approved=True,
    )

    decision = AgentExecutionPolicy().authorize(agent, task, tool)

    assert decision.allowed is False
    assert decision.reason == "tool capability does not match task capability"


def test_agent_execution_policy_denies_unapproved_tool():
    agent, task, tool = build_context()

    tool = AgentTool(
        name="research-reader",
        capability=task.capability,
        description="Read approved research sources.",
        approved=False,
    )

    decision = AgentExecutionPolicy().authorize(agent, task, tool)

    assert decision.allowed is False
    assert decision.reason == "tool is not approved"
