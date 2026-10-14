from uuid import uuid4

import pytest

from app.modules.agent.domain.execution import AgentCapability, AgentTool
from app.modules.agent.domain.tool_registry import AgentToolRegistry


def make_tool(
    name="research-reader",
    capability=AgentCapability.RESEARCH,
    approved=False,
):
    return AgentTool(
        name=name,
        capability=capability,
        description="Read approved research sources.",
        approved=approved,
    )


def test_registry_registers_and_retrieves_tool():
    registry = AgentToolRegistry()
    tool = make_tool()

    entry = registry.register(tool)

    assert entry.registered is True
    assert registry.get(tool.name) == tool
    assert registry.contains(tool.name) is True
    assert len(registry) == 1


def test_registry_rejects_duplicate_tool_name():
    registry = AgentToolRegistry()
    registry.register(make_tool())

    with pytest.raises(ValueError, match="tool already registered"):
        registry.register(make_tool())


def test_registry_rejects_invalid_tool():
    registry = AgentToolRegistry()

    with pytest.raises(TypeError, match="tool must be an AgentTool"):
        registry.register("not-a-tool")


def test_registry_require_raises_for_unknown_tool():
    registry = AgentToolRegistry()

    with pytest.raises(KeyError, match="tool not registered"):
        registry.require("missing-tool")


def test_registry_filters_tools_by_capability():
    registry = AgentToolRegistry()

    research = make_tool(
        name="research-reader",
        capability=AgentCapability.RESEARCH,
    )
    finance = make_tool(
        name="finance-reader",
        capability=AgentCapability.FINANCE,
    )

    registry.register(research)
    registry.register(finance)

    assert registry.list_for_capability(AgentCapability.RESEARCH) == (research,)
    assert registry.list_for_capability(AgentCapability.FINANCE) == (finance,)


def test_registry_does_not_infer_approval():
    registry = AgentToolRegistry()
    tool = make_tool(approved=False)

    registry.register(tool)

    assert registry.require(tool.name).approved is False
