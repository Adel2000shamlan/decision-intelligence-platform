import pytest

from app.modules.release import (
    ReleaseChecklist,
    ReleaseGate,
    RollbackPlan,
)


def test_release_checklist_requires_all_gates():
    checklist = ReleaseChecklist(
        (
            ReleaseGate("tests", True, "all tests passed"),
            ReleaseGate("security", True, "security checks passed"),
            ReleaseGate("rollback", True, "rollback verified"),
        )
    )
    assert checklist.passed is True
    checklist.require()


def test_release_checklist_blocks_failed_gate():
    checklist = ReleaseChecklist(
        (
            ReleaseGate("tests", True, "passed"),
            ReleaseGate("security", False, "failed"),
        )
    )
    assert checklist.passed is False
    with pytest.raises(RuntimeError):
        checklist.require()


def test_rollback_deploys_previous_release():
    deployed = []

    plan = RollbackPlan(
        release_id="v111.1",
        previous_release_id="v110.2",
        reason="critical pilot regression",
    )

    result = plan.execute(deployed.append)

    assert result == "v110.2"
    assert deployed == ["v110.2"]
