from uuid import uuid4

from app.modules.memory.domain.models import MemoryItem, MemoryStatus, MemoryType
from app.modules.memory.persistence.sqlite import SQLiteMemoryRepository


def make_memory(tenant_id, memory_type=MemoryType.FACT, content="memory"):
    return MemoryItem.create(
        tenant_id=tenant_id,
        memory_type=memory_type,
        content=content,
        source="verified_test_source",
        evidence_ids=(uuid4(),),
        confidence=0.8,
    )


def test_memory_repository_save_and_get():
    tenant_id = uuid4()
    repo = SQLiteMemoryRepository()
    item = make_memory(tenant_id)

    repo.save(item)

    loaded = repo.get(tenant_id, item.id)

    assert loaded == item


def test_memory_repository_tenant_isolation():
    tenant_a = uuid4()
    tenant_b = uuid4()
    repo = SQLiteMemoryRepository()
    item = make_memory(tenant_a)

    repo.save(item)

    assert repo.get(tenant_b, item.id) is None
    assert repo.list(tenant_b) == ()


def test_memory_repository_list_filters_type_and_status():
    tenant_id = uuid4()
    repo = SQLiteMemoryRepository()

    fact = make_memory(tenant_id, MemoryType.FACT, "fact")
    observation = make_memory(
        tenant_id,
        MemoryType.OBSERVATION,
        "observation",
    )

    repo.save(fact)
    repo.save(observation)

    assert repo.list(tenant_id, memory_type=MemoryType.FACT) == (fact,)
    assert repo.list(
        tenant_id,
        memory_type=MemoryType.OBSERVATION,
    ) == (observation,)

    archived = MemoryItem(
        id=fact.id,
        tenant_id=fact.tenant_id,
        memory_type=fact.memory_type,
        content=fact.content,
        source=fact.source,
        evidence_ids=fact.evidence_ids,
        confidence=fact.confidence,
        status=MemoryStatus.ARCHIVED,
        created_at=fact.created_at,
        expires_at=fact.expires_at,
        version=2,
    )
    repo.save(archived)

    assert repo.list(
        tenant_id,
        status=MemoryStatus.ARCHIVED,
    ) == (archived,)


def test_memory_repository_preserves_evidence_and_version():
    tenant_id = uuid4()
    repo = SQLiteMemoryRepository()
    item = make_memory(tenant_id)

    updated = MemoryItem(
        id=item.id,
        tenant_id=item.tenant_id,
        memory_type=MemoryType.INSIGHT,
        content="updated insight",
        source=item.source,
        evidence_ids=item.evidence_ids,
        confidence=0.91,
        status=MemoryStatus.SUPERSEDED,
        created_at=item.created_at,
        expires_at=item.expires_at,
        version=2,
    )

    repo.save(updated)

    loaded = repo.get(tenant_id, item.id)

    assert loaded == updated
    assert loaded.evidence_ids == item.evidence_ids
    assert loaded.version == 2


def test_memory_repository_delete_is_tenant_scoped():
    tenant_a = uuid4()
    tenant_b = uuid4()
    repo = SQLiteMemoryRepository()
    item = make_memory(tenant_a)

    repo.save(item)
    repo.delete(tenant_b, item.id)

    assert repo.get(tenant_a, item.id) == item

    repo.delete(tenant_a, item.id)

    assert repo.get(tenant_a, item.id) is None
