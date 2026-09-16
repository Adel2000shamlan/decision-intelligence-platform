import pytest

from app.modules.launch import (
    LaunchGate,
    LaunchStatus,
    MVPLaunchService,
)


def test_mvp_is_ready_when_critical_gates_pass():
    service = MVPLaunchService()

    launch = service.evaluate(
        "v111.1",
        (
            LaunchGate("tests", True, True, "passed"),
            LaunchGate("security", True, True, "passed"),
            LaunchGate("support", True, False, "configured"),
        ),
    )

    assert launch.status == LaunchStatus.READY
    assert launch.ready is True

    released = service.release(launch)
    assert released.status == LaunchStatus.RELEASED


def test_failed_critical_gate_blocks_release():
    service = MVPLaunchService()

    launch = service.evaluate(
        "v111.1",
        (
            LaunchGate("tests", True, True, "passed"),
            LaunchGate("security", False, True, "failed"),
        ),
    )

    assert launch.status == LaunchStatus.NOT_READY
    assert launch.ready is False

    with pytest.raises(RuntimeError):
        service.release(launch)


def test_failed_noncritical_gate_does_not_block_release():
    service = MVPLaunchService()

    launch = service.evaluate(
        "v111.1",
        (
            LaunchGate("tests", True, True, "passed"),
            LaunchGate("documentation", False, False, "pending"),
        ),
    )

    assert launch.ready is True
    assert service.release(launch).status == LaunchStatus.RELEASED


def test_rollback_requires_released_mvp():
    service = MVPLaunchService()

    launch = service.evaluate(
        "v111.1",
        (LaunchGate("tests", True, True, "passed"),),
    )

    with pytest.raises(ValueError):
        service.rollback(launch)

    released = service.release(launch)
    rolled_back = service.rollback(released)

    assert rolled_back.status == LaunchStatus.ROLLED_BACK
