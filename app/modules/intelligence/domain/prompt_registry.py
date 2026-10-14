from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PromptDefinition:
    task: str
    version: str
    template: str

    def __post_init__(self) -> None:
        for name in ("task", "version", "template"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")


class PromptRegistry:
    """Deterministic prompt/version registry."""

    def __init__(self) -> None:
        self._items: dict[tuple[str, str], PromptDefinition] = {}

    def register(self, prompt: PromptDefinition) -> PromptDefinition:
        key = (prompt.task.strip().lower(), prompt.version.strip())

        if key in self._items:
            raise ValueError("prompt version already registered")

        normalized = PromptDefinition(
            task=key[0],
            version=key[1],
            template=prompt.template.strip(),
        )

        self._items[key] = normalized
        return normalized

    def get(self, task: str, version: str) -> PromptDefinition | None:
        if not isinstance(task, str) or not task.strip():
            raise ValueError("task is required")

        if not isinstance(version, str) or not version.strip():
            raise ValueError("version is required")

        return self._items.get(
            (task.strip().lower(), version.strip())
        )
