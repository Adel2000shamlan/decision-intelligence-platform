from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelRoute:
    task: str
    model: str
    policy_id: str

    def __post_init__(self) -> None:
        for name in ("task", "model", "policy_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")


class ModelRoutingPolicy:
    """Deterministic model selection; no provider call is performed."""

    policy_id = "intelligence.model-routing.v1"

    _ROUTES = {
        "analysis": "default-analysis",
        "decision": "default-decision",
        "scenario": "default-scenario",
        "risk": "default-risk",
    }

    def route(self, task: str) -> ModelRoute:
        if not isinstance(task, str) or not task.strip():
            raise ValueError("task is required")

        normalized = task.strip().lower()

        try:
            model = self._ROUTES[normalized]
        except KeyError as exc:
            raise ValueError(f"unsupported intelligence task: {normalized}") from exc

        return ModelRoute(
            task=normalized,
            model=model,
            policy_id=self.policy_id,
        )
