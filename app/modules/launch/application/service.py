from app.modules.launch.domain.models import (
    LaunchGate,
    LaunchStatus,
    MVPLaunch,
)


class MVPLaunchService:
    def evaluate(
        self,
        release_id: str,
        gates: tuple[LaunchGate, ...],
    ) -> MVPLaunch:
        launch = MVPLaunch(
            release_id=release_id,
            status=(
                LaunchStatus.READY
                if gates and all(
                    gate.passed
                    for gate in gates
                    if gate.critical
                )
                else LaunchStatus.NOT_READY
            ),
            gates=gates,
        )
        return launch

    def release(self, launch: MVPLaunch) -> MVPLaunch:
        return launch.release()

    def rollback(self, launch: MVPLaunch) -> MVPLaunch:
        return launch.rollback()
