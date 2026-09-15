from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from app.modules.intelligence.domain.gateway import (
    AIGateway,
    AIGatewayRequest,
    AIGatewayResponse,
)
from app.modules.intelligence.domain.model_routing import (
    ModelRoutingPolicy,
)
from app.modules.intelligence.domain.prompt_registry import (
    PromptRegistry,
)


@dataclass(frozen=True, slots=True)
class IntelligenceGatewayResult:
    request_id: UUID
    model: str
    provider: str
    prompt_version: str
    output: object


class LocalAIGateway:
    """Deterministic local gateway; performs no external AI call."""

    provider = "local"

    def generate(self, request: AIGatewayRequest) -> AIGatewayResponse:
        return AIGatewayResponse(
            request_id=uuid4(),
            model=request.model,
            output={
                "task": request.task,
                "status": "gateway-accepted",
            },
            provider=self.provider,
            prompt_version=request.prompt_version,
        )


class IntelligenceGatewayService:
    """Routes intelligence requests through explicit model and prompt policies."""

    def __init__(
        self,
        gateway: AIGateway | None = None,
        routing: ModelRoutingPolicy | None = None,
        prompts: PromptRegistry | None = None,
    ) -> None:
        self.gateway = gateway or LocalAIGateway()
        self.routing = routing or ModelRoutingPolicy()
        self.prompts = prompts or PromptRegistry()

    def generate(
        self,
        tenant_id: UUID,
        actor_id: UUID,
        correlation_id: UUID,
        task: str,
        prompt_version: str,
    ) -> IntelligenceGatewayResult:
        route = self.routing.route(task)

        prompt = self.prompts.get(task, prompt_version)
        if prompt is None:
            raise ValueError(
                f"prompt version not registered: {task}:{prompt_version}"
            )

        request = AIGatewayRequest(
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            task=route.task,
            model=route.model,
            prompt_version=prompt.version,
        )

        response = self.gateway.generate(request)

        return IntelligenceGatewayResult(
            request_id=response.request_id,
            model=response.model,
            provider=response.provider,
            prompt_version=response.prompt_version,
            output=response.output,
        )
