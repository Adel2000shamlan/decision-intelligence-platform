from __future__ import annotations

from dataclasses import dataclass

from app.modules.agent.domain.execution import AgentCapability, AgentTask, AgentTool
from app.modules.agent.domain.models import Agent


@dataclass(frozen=True, slots=True)
class AgentPolicyDecision:
    allowed: bool
    reason: str
    policy_id: str = "agent.execution-boundary.v1"


class AgentExecutionPolicy:
    """Deterministic, fail-closed boundary for agent task execution."""

    policy_id = "agent.execution-boundary.v1"

    def authorize(
        self,
        agent: Agent,
        task: AgentTask,
        tool: AgentTool,
    ) -> AgentPolicyDecision:
        if not isinstance(agent, Agent):
            return AgentPolicyDecision(False, "invalid agent")

        if not agent.enabled:
            return AgentPolicyDecision(False, "agent is disabled")

        if agent.tenant_id != task.tenant_id:
            return AgentPolicyDecision(False, "agent tenant mismatch")

        if agent.id != task.agent_id:
            return AgentPolicyDecision(False, "task agent mismatch")

        if task.capability not in agent.capabilities:
            return AgentPolicyDecision(
                False,
                "agent capability is not registered",
            )

        if tool.capability is not task.capability:
            return AgentPolicyDecision(
                False,
                "tool capability does not match task capability",
            )

        if not tool.approved:
            return AgentPolicyDecision(
                False,
                "tool is not approved",
            )

        return AgentPolicyDecision(
            True,
            "agent execution boundary satisfied",
        )
