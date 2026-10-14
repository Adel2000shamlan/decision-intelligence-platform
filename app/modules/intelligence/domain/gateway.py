from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AIGatewayRequest:
    tenant_id: UUID
    actor_id: UUID
    correlation_id: UUID
    task: str
    model: str
    prompt_version: str

    def __post_init__(self) -> None:
        for name in ("tenant_id", "actor_id", "correlation_id"):
            if not isinstance(getattr(self, name), UUID):
                raise ValueError(f"{name} must be UUID")

        for name in ("task", "model", "prompt_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")


@dataclass(frozen=True, slots=True)
class AIGatewayResponse:
    request_id: UUID
    model: str
    output: object
    provider: str
    prompt_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, UUID):
            raise ValueError("request_id must be UUID")

        for name in ("model", "provider", "prompt_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")


class AIGateway(Protocol):
    def generate(self, request: AIGatewayRequest) -> AIGatewayResponse:
        ...
