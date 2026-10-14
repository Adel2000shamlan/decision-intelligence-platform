from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.modules.memory.domain.models import (
    MemoryItem,
    MemoryStatus,
    MemoryType,
)
from app.shared.domain.errors import InvalidDomainData


def test_create_memory_item():
    tenant_id = uuid4()
    evidence_id = uuid4()

    item = MemoryItem.create(
        tenant_id=tenant_id,
        memory_type=MemoryType.FACT,
        content="Confirmed operating cost",
        source="verified_record",
        evidence_ids=(evidence_id,),
        confidence=0.95,
    )

    assert item.tenant_id == tenant_id
    assert item.memory_type is MemoryType.FACT
    assert item.status is MemoryStatus.ACTIVE
    assert item.evidence_ids == (evidence_id,)
    assert item.confidence == 0.95
    assert item.version == 1


def test_memory_requires_content_and_source():
    with pytest.raises(InvalidDomainData):
        MemoryItem.create(uuid4(), MemoryType.FACT, "", "source")

    with pytest.raises(InvalidDomainData):
        MemoryItem.create(uuid4(), MemoryType.FACT, "content", "")


def test_memory_rejects_invalid_confidence():
    for value in (-0.01, 1.01, True):
        with pytest.raises(InvalidDomainData):
            MemoryItem.create(
                uuid4(),
                MemoryType.FACT,
                "content",
                "source",
                confidence=value,
            )


def test_memory_rejects_invalid_evidence_ids():
    with pytest.raises(InvalidDomainData):
        MemoryItem.create(
            uuid4(),
            MemoryType.FACT,
            "content",
            "source",
            evidence_ids=(uuid4(), "not-a-uuid"),
        )


def test_memory_expiry_must_be_future_and_timezone_aware():
    with pytest.raises(InvalidDomainData):
        MemoryItem.create(
            uuid4(),
            MemoryType.FACT,
            "content",
            "source",
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )

    with pytest.raises(InvalidDomainData):
        MemoryItem.create(
            uuid4(),
            MemoryType.FACT,
            "content",
            "source",
            expires_at=datetime.now(),
        )


def test_memory_is_tenant_scoped():
    tenant_a = uuid4()
    tenant_b = uuid4()

    a = MemoryItem.create(
        tenant_a,
        MemoryType.OBSERVATION,
        "Observation A",
        "test",
    )
    b = MemoryItem.create(
        tenant_b,
        MemoryType.OBSERVATION,
        "Observation B",
        "test",
    )

    assert a.tenant_id != b.tenant_id
