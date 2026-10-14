from dataclasses import dataclass
from enum import Enum


class LaunchStatus(str, Enum):
    NOT_READY = "not_ready"
    READY = "ready"
    RELEASED = "released"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True, slots=True)
class LaunchGate:
    name: str
    passed: bool
    critical: bool
    evidence: str


@dataclass(frozen=True, slots=True)
class MVPLaunch:
    release_id: str
    status: LaunchStatus
    gates: tuple[LaunchGate, ...]

    @property
    def ready(self) -> bool:
        return bool(self.gates) and all(
            gate.passed for gate in self.gates if gate.critical
        )

    def require_ready(self) -> None:
        if not self.ready:
            failed = ", ".join(
                gate.name
                for gate in self.gates
                if gate.critical and not gate.passed
            )
            raise RuntimeError(
                f"mvp launch blocked by critical gates: {failed}"
            )

    def release(self) -> "MVPLaunch":
        self.require_ready()
        if self.status not in (
            LaunchStatus.READY,
            LaunchStatus.NOT_READY,
        ):
            raise ValueError("release is not valid from current launch status")
        return MVPLaunch(
            release_id=self.release_id,
            status=LaunchStatus.RELEASED,
            gates=self.gates,
        )

    def rollback(self) -> "MVPLaunch":
        if self.status != LaunchStatus.RELEASED:
            raise ValueError("only a released MVP can be rolled back")
        return MVPLaunch(
            release_id=self.release_id,
            status=LaunchStatus.ROLLED_BACK,
            gates=self.gates,
        )
