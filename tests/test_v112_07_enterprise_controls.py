from uuid import uuid4

from app.modules.authorization.domain.advanced_controls import (
    CONTROL_REGISTRY,
    ControlContext,
    evaluate_all,
    master_status,
)


def ctx(**overrides):
    base = dict(
        actor_id=uuid4(),
        tenant_id=uuid4(),
        action="read",
        resource_type="project",
        resource_id=uuid4(),
        actor_type="human",
        authenticated=True,
        assurance="strong",
        permission_granted=True,
        policy_version="v1",
    )
    base.update(overrides)
    return ControlContext(**base)


def test_v112_07_enterprise_control_inventory_is_complete():
    stages = [stage for stage, _, _ in CONTROL_REGISTRY]

    assert stages == list(range(11, 101))
    assert len(CONTROL_REGISTRY) == 90


def test_v112_07_full_enterprise_gate_passes():
    results = evaluate_all(ctx())

    assert len(results) == 90
    assert results[0].stage == 11
    assert results[-1].stage == 100
    assert all(result.allowed for result in results)
    assert master_status(ctx()) is True


def test_v112_07_fail_closed_short_circuits_at_first_failed_control():
    results = evaluate_all(
        ctx(attributes={"unknown_request": True})
    )

    assert results[-1].stage == 78
    assert results[-1].allowed is False
    assert len(results) == 68
    assert master_status(
        ctx(attributes={"unknown_request": True})
    ) is False


def test_v112_07_tenant_boundary_denies_cross_tenant_access():
    results = evaluate_all(
        ctx(attributes={"cross_tenant": True})
    )

    assert results[-1].stage == 23
    assert results[-1].allowed is False
    assert master_status(
        ctx(attributes={"cross_tenant": True})
    ) is False


def test_v112_07_ai_tool_boundary_is_enforced():
    results = evaluate_all(
        ctx(
            actor_type="ai",
            attributes={
                "agent_capability_allowed": True,
                "tool_unapproved": True,
            },
        )
    )

    assert results[-1].stage == 57
    assert results[-1].allowed is False
    assert master_status(
        ctx(
            actor_type="ai",
            attributes={
                "agent_capability_allowed": True,
                "tool_unapproved": True,
            },
        )
    ) is False


def test_v112_07_human_in_the_loop_gate_is_enforced():
    results = evaluate_all(
        ctx(
            action="execute",
            attributes={
                "human_confirmation_required": True,
                "human_confirmed": False,
            },
        )
    )

    assert results[-1].stage == 59
    assert results[-1].allowed is False


def test_v112_07_release_gate_is_reachable_and_enforced():
    results = evaluate_all(
        ctx(attributes={"release_gate_failed": True})
    )

    assert results[-1].stage == 99
    assert results[-1].allowed is False


def test_v112_07_master_closure_is_reachable():
    results = evaluate_all(ctx())

    assert results[-1].stage == 100
    assert results[-1].allowed is True
    assert master_status(ctx()) is True
