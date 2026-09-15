from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.modules.agent.domain.evidence import AgentEvidenceSet
from app.modules.agent.domain.execution import (
    AgentExecutionResult,
    AgentExecutionStatus,
    AgentTask,
)
from app.modules.agent.domain.models import Agent
from app.modules.agent.domain.policy import AgentExecutionPolicy
from app.modules.agent.domain.tool_registry import AgentToolRegistry


@dataclass(frozen=True, slots=True)
class AgentExecutionReceipt:
    result: AgentExecutionResult
    policy_id: str


class AgentOrchestrator:
    """Deterministic execution boundary for registered agents.

    The orchestrator never approves sensitive business actions. It only
    executes an explicitly registered and policy-authorized tool.
    """

    def __init__(
        self,
        registry: AgentToolRegistry,
        policy: AgentExecutionPolicy | None = None,
    ) -> None:
        self._registry = registry
        self._policy = policy or AgentExecutionPolicy()

    def execute(
        self,
        agent: Agent,
        task: AgentTask,
        tool_name: str,
        handler: Callable[[AgentTask], object],
        evidence: AgentEvidenceSet | None = None,
    ) -> AgentExecutionReceipt:
        tool = self._registry.get(tool_name)

        if tool is None:
            return AgentExecutionReceipt(
                result=AgentExecutionResult(
                    task_id=task.task_id,
                    agent_id=agent.id,
                    status=AgentExecutionStatus.DENIED,
                    output={"reason": "tool not registered"},
                ),
                policy_id=self._policy.policy_id,
            )

        decision = self._policy.authorize(agent, task, tool)

        if not decision.allowed:
            return AgentExecutionReceipt(
                result=AgentExecutionResult(
                    task_id=task.task_id,
                    agent_id=agent.id,
                    status=AgentExecutionStatus.DENIED,
                    output={"reason": decision.reason},
                ),
                policy_id=decision.policy_id,
            )

        if evidence is None:
            return AgentExecutionReceipt(
                result=AgentExecutionResult(
                    task_id=task.task_id,
                    agent_id=agent.id,
                    status=AgentExecutionStatus.DENIED,
                    output={"reason": "execution evidence is required"},
                ),
                policy_id=decision.policy_id,
            )

        if not isinstance(evidence, AgentEvidenceSet):
            return AgentExecutionReceipt(
                result=AgentExecutionResult(
                    task_id=task.task_id,
                    agent_id=agent.id,
                    status=AgentExecutionStatus.DENIED,
                    output={"reason": "invalid execution evidence"},
                ),
                policy_id=decision.policy_id,
            )

        if evidence.tenant_id != task.tenant_id:
            return AgentExecutionReceipt(
                result=AgentExecutionResult(
                    task_id=task.task_id,
                    agent_id=agent.id,
                    status=AgentExecutionStatus.DENIED,
                    output={"reason": "evidence tenant mismatch"},
                ),
                policy_id=decision.policy_id,
            )

        try:
            evidence.require()
        except ValueError as exc:
            return AgentExecutionReceipt(
                result=AgentExecutionResult(
                    task_id=task.task_id,
                    agent_id=agent.id,
                    status=AgentExecutionStatus.DENIED,
                    output={"reason": str(exc)},
                ),
                policy_id=decision.policy_id,
            )

        try:
            output = handler(task)
        except Exception as exc:
            return AgentExecutionReceipt(
                result=AgentExecutionResult(
                    task_id=task.task_id,
                    agent_id=agent.id,
                    status=AgentExecutionStatus.FAILED,
                    output={"reason": "execution failed", "error": str(exc)},
                    evidence_ids=evidence.evidence_ids,
                ),
                policy_id=decision.policy_id,
            )

        return AgentExecutionReceipt(
            result=AgentExecutionResult(
                task_id=task.task_id,
                agent_id=agent.id,
                status=AgentExecutionStatus.COMPLETED,
                output=output,
                    evidence_ids=evidence.evidence_ids,
            ),
            policy_id=decision.policy_id,
        )
