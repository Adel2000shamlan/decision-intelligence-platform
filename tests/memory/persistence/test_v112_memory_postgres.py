import os
from uuid import uuid4

import pytest
import psycopg

from app.modules.memory.domain.models import MemoryItem, MemoryStatus, MemoryType
from app.modules.memory.persistence.postgres import PostgresMemoryRepository


DATABASE_URL = os.getenv("DATABASE_URL")


pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL is not configured",
)


def make_memory(tenant_id, memory_type=MemoryType.FACT, content="memory"):
    return MemoryItem.create(
        tenant_id=tenant_id,
        memory_type=memory_type,
        content=content,
        source="verified_postgres_test_source",
        evidence_ids=(uuid4(),),
        confidence=0.8,
    )


@pytest.fixture
def repository():
    conn = psycopg.connect(DATABASE_URL)
    repo = PostgresMemoryRepository(conn)

    with conn.cursor() as cur:
        cur.execute("DELETE FROM memory_items")

    conn.commit()

    yield repo

    with conn.cursor() as cur:
        cur.execute("DELETE FROM memory_items")

    conn.commit()
    conn.close()


def test_postgres_memory_repository_save_and_get(repository):
    tenant_id = uuid4()
    item = make_memory(tenant_id)

    repository.save(item)

    loaded = repository.get(tenant_id, item.id)

    assert loaded == item


def test_postgres_memory_repository_tenant_isolation(repository):
    tenant_a = uuid4()
    tenant_b = uuid4()
    item = make_memory(tenant_a)

    repository.save(item)

    assert repository.get(tenant_b, item.id) is None
    assert repository.list(tenant_b) == ()


def test_postgres_memory_repository_list_filters(repository):
    tenant_id = uuid4()

    fact = make_memory(
        tenant_id,
        MemoryType.FACT,
        "fact",
    )
    observation = make_memory(
        tenant_id,
        MemoryType.OBSERVATION,
        "observation",
    )

    repository.save(fact)
    repository.save(observation)

    assert repository.list(
        tenant_id,
        memory_type=MemoryType.FACT,
    ) == (fact,)

    assert repository.list(
        tenant_id,
        memory_type=MemoryType.OBSERVATION,
    ) == (observation,)


def test_postgres_memory_repository_preserves_evidence_and_version(repository):
    tenant_id = uuid4()
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

    repository.save(item)
    repository.save(updated)

    loaded = repository.get(tenant_id, item.id)

    assert loaded == updated
    assert loaded.evidence_ids == item.evidence_ids
    assert loaded.version == 2


def test_postgres_memory_repository_delete_is_tenant_scoped(repository):
    tenant_a = uuid4()
    tenant_b = uuid4()
    item = make_memory(tenant_a)

    repository.save(item)

    repository.delete(tenant_b, item.id)

    assert repository.get(tenant_a, item.id) == item

    repository.delete(tenant_a, item.id)

    assert repository.get(tenant_a, item.id) is None
