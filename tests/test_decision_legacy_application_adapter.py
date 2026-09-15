import pytest
from uuid import uuid4

from app.modules.decision.application.implementation import (
    DecisionApplicationService,
)
from app.modules.decision.compatibility.legacy import (
    LegacyMigrationDisposition,
    migrate_legacy_result,
)
from app.modules.decision.compatibility.application import (
    LegacyDecisionApplicationAdapter,
)


def test_adapter_executes_only_create_migration_result():
    organization_id = uuid4()
    project_id = uuid4()

    result = migrate_legacy_result(
        legacy_id="legacy-adapter-001",
        organization_id=organization_id,
        project_id=project_id,
        title="Adapter decision",
        objective="Legacy objective",
        description="Explicit official description",
        legacy_status="draft",
        legacy_version=1,
    )

    assert result.disposition is LegacyMigrationDisposition.CREATE

    service = DecisionApplicationService.in_memory()
    adapter = LegacyDecisionApplicationAdapter(service)

    decision = adapter.execute(result)

    assert decision.organization_id == organization_id
    assert decision.project_id == project_id
    assert decision.title == "Adapter decision"
    assert decision.description == "Explicit official description"


def test_adapter_rejects_link_result_without_executing_it():
    official_id = uuid4()

    result = migrate_legacy_result(
        legacy_id="legacy-adapter-link-001",
        organization_id=uuid4(),
        project_id=uuid4(),
        title="Linked decision",
        objective="Legacy objective",
        description="Explicit official description",
        legacy_status="validated",
        legacy_version=2,
        official_id=official_id,
        official_status=__import__(
            "app.modules.decision.domain.models",
            fromlist=["DecisionStatus"],
        ).DecisionStatus.ANALYSIS,
    )

    assert result.disposition is LegacyMigrationDisposition.LINK

    service = DecisionApplicationService.in_memory()
    adapter = LegacyDecisionApplicationAdapter(service)

    try:
        adapter.execute(result)
        assert False, "LINK result must not be executed by the adapter"
    except ValueError as exc:
        assert "CREATE" in str(exc)

    assert service.list() == []


def test_adapter_rejects_non_migration_result():
    service = DecisionApplicationService.in_memory()
    adapter = LegacyDecisionApplicationAdapter(service)

    try:
        adapter.execute(object())
        assert False, "adapter must reject invalid migration result type"
    except TypeError as exc:
        assert "LegacyMigrationResult" in str(exc)

    assert service.list() == []

def test_adapter_rejects_create_result_with_invalid_payload():
    from app.modules.decision.compatibility.application import (
        LegacyDecisionApplicationAdapter,
    )
    from app.modules.decision.compatibility.legacy import (
        LegacyMigrationDisposition,
        LegacyMigrationResult,
    )
    from app.modules.decision.application.implementation import (
        DecisionApplicationService,
    )
    from app.modules.decision.domain.models import DecisionStatus

    service = DecisionApplicationService.in_memory()
    adapter = LegacyDecisionApplicationAdapter(service)

    result = LegacyMigrationResult(
        legacy_id="legacy-1",
        disposition=LegacyMigrationDisposition.CREATE,
        official_status=DecisionStatus.DRAFT,
        payload=object(),
    )

    with pytest.raises(TypeError, match="CreateDecision"):
        adapter.execute(result)

    assert service.list() == []
