from __future__ import annotations

from dataclasses import dataclass

from app.modules.agent.domain.execution import AgentCapability, AgentTool


@dataclass(frozen=True, slots=True)
class ToolRegistryEntry:
    tool: AgentTool
    registered: bool = True


class AgentToolRegistry:
    """Deterministic registry for agent tools.

    Registration is explicit. Tool approval remains a separate execution
    policy concern and is never inferred from registration.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolRegistryEntry] = {}

    def register(self, tool: AgentTool) -> ToolRegistryEntry:
        if not isinstance(tool, AgentTool):
            raise TypeError("tool must be an AgentTool")

        key = tool.name.strip()
        if not key:
            raise ValueError("tool name required")

        if key in self._tools:
            raise ValueError("tool already registered")

        entry = ToolRegistryEntry(tool=tool)
        self._tools[key] = entry
        return entry

    def get(self, name: str) -> AgentTool | None:
        if not isinstance(name, str) or not name.strip():
            return None

        entry = self._tools.get(name.strip())
        return entry.tool if entry is not None else None

    def require(self, name: str) -> AgentTool:
        tool = self.get(name)
        if tool is None:
            raise KeyError("tool not registered")
        return tool

    def list_for_capability(
        self,
        capability: AgentCapability,
    ) -> tuple[AgentTool, ...]:
        capability = AgentCapability(capability)
        return tuple(
            entry.tool
            for entry in self._tools.values()
            if entry.tool.capability == capability
        )

    def contains(self, name: str) -> bool:
        return self.get(name) is not None

    def __len__(self) -> int:
        return len(self._tools)
