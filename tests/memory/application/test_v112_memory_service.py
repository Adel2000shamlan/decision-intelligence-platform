from datetime import timedelta
from uuid import uuid4

import pytest

from app.modules.memory.application.service import MemoryService
from app.modules.memory.domain.models import MemoryStatus, MemoryType
from app.modules.memory.persistence.sqlite import SQLiteMemoryRepository
from app.shared.domain.errors import BusinessRuleViolation


def make_service():
    return MemoryService(SQLiteMemoryRepository())


def test_remember_and_get():
    service = make_service()
    tenant_id = uuid4()

    item = service.remember(
        tenant_id=tenant_id,
        memory_type=MemoryType.FACT,
        content="Revenue increased",
        source="monthly_report",
        confidence=0.9,
    )

    loaded = service.get(tenant_id, item.id)

    assert loaded == item
    assert loaded.status is MemoryStatus.ACTIVE


def test_list_filters_by_type_and_status():
    service = make_service()
    tenant_id = uuid4()

    service.remember(
        tenant_id=tenant_id,
        memory_type=MemoryType.FACT,
        content="fact",
        source="source",
    )
    service.remember(
        tenant_id=tenant_id,
        memory_type=MemoryType.OBSERVATION,
        content="observation",
        source="source",
    )

    facts = service.list(tenant_id, memory_type=MemoryType.FACT)

    assert len(facts) == 1
    assert facts[0].memory_type is MemoryType.FACT


def test_supersede_increments_version():
    service = make_service()
    tenant_id = uuid4()

    item = service.remember(
        tenant_id=tenant_id,
        memory_type=MemoryType.INSIGHT,
        content="old insight",
        source="analysis",
    )

    replacement = service.supersede(
        tenant_id=tenant_id,
        memory_id=item.id,
        content="updated insight",
        source="new_analysis",
        confidence=0.8,
    )

    assert replacement.id == item.id
    assert replacement.version == item.version + 1
    assert replacement.status is MemoryStatus.SUPERSEDED
    assert replacement.content == "updated insight"


def test_cannot_supersede_non_active_memory():
    service = make_service()
    tenant_id = uuid4()

    item = service.remember(
        tenant_id=tenant_id,
        memory_type=MemoryType.FACT,
        content="fact",
        source="source",
    )

    service.archive(tenant_id, item.id)

    with pytest.raises(BusinessRuleViolation):
        service.supersede(
            tenant_id=tenant_id,
            memory_id=item.id,
            content="replacement",
            source="source",
        )


def test_archive_is_idempotent():
    service = make_service()
    tenant_id = uuid4()

    item = service.remember(
        tenant_id=tenant_id,
        memory_type=MemoryType.PREFERENCE,
        content="preference",
        source="user",
    )

    archived = service.archive(tenant_id, item.id)
    archived_again = service.archive(tenant_id, item.id)

    assert archived.status is MemoryStatus.ARCHIVED
    assert archived_again.status is MemoryStatus.ARCHIVED
    assert archived_again.version == archived.version


def test_missing_memory_raises():
    service = make_service()
    tenant_id = uuid4()

    with pytest.raises(BusinessRuleViolation):
        service.supersede(
            tenant_id=tenant_id,
            memory_id=uuid4(),
            content="replacement",
            source="source",
        )

    with pytest.raises(BusinessRuleViolation):
        service.archive(tenant_id, uuid4())


def test_forget_is_tenant_scoped():
    service = make_service()
    tenant_a = uuid4()
    tenant_b = uuid4()

    item = service.remember(
        tenant_id=tenant_a,
        memory_type=MemoryType.FACT,
        content="tenant A fact",
        source="source",
    )

    assert service.get(tenant_b, item.id) is None

    service.forget(tenant_b, item.id)

    assert service.get(tenant_a, item.id) == item

    service.forget(tenant_a, item.id)

    assert service.get(tenant_a, item.id) is None
