from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True, slots=True)
class ReleaseGate:
    name: str
    passed: bool
    evidence: str


@dataclass(frozen=True, slots=True)
class ReleaseChecklist:
    gates: tuple[ReleaseGate, ...]

    @property
    def passed(self) -> bool:
        return bool(self.gates) and all(gate.passed for gate in self.gates)

    def require(self) -> None:
        if not self.passed:
            failed = ", ".join(
                gate.name for gate in self.gates if not gate.passed
            )
            raise RuntimeError(
                f"release checklist failed: {failed}"
            )


@dataclass(frozen=True, slots=True)
class RollbackPlan:
    release_id: str
    previous_release_id: str
    reason: str

    def execute(self, deploy: Callable[[str], None]) -> str:
        if not self.previous_release_id.strip():
            raise ValueError("previous release must be defined")
        deploy(self.previous_release_id)
        return self.previous_release_id
