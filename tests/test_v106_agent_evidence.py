from uuid import uuid4

import pytest

from app.modules.agent.domain.evidence import AgentEvidenceSet
from app.modules.intelligence.domain.evidence import Evidence, EvidenceType


def make_evidence(tenant_id, traceable=True):
    return Evidence(
        evidence_id=uuid4(),
        tenant_id=tenant_id,
        evidence_type=EvidenceType.SOURCE,
        source="test-source",
        reference="test-reference",
        statement="Verified market observation.",
        traceable=traceable,
    )


def test_agent_evidence_set_accepts_same_tenant_traceable_evidence():
    tenant_id = uuid4()
    evidence = make_evidence(tenant_id)

    evidence_set = AgentEvidenceSet(
        tenant_id=tenant_id,
        evidence=(evidence,),
    )

    assert evidence_set.evidence_ids == (evidence.evidence_id,)
    assert evidence_set.require() == (evidence,)


def test_agent_evidence_set_rejects_cross_tenant_evidence():
    tenant_id = uuid4()
    other_tenant_id = uuid4()

    with pytest.raises(ValueError, match="evidence tenant mismatch"):
        AgentEvidenceSet(
            tenant_id=tenant_id,
            evidence=(make_evidence(other_tenant_id),),
        )


def test_agent_evidence_set_rejects_untraceable_evidence():
    tenant_id = uuid4()

    with pytest.raises(ValueError, match="evidence must be traceable"):
        AgentEvidenceSet(
            tenant_id=tenant_id,
            evidence=(make_evidence(tenant_id, traceable=False),),
        )


def test_agent_evidence_set_rejects_non_evidence_values():
    tenant_id = uuid4()

    with pytest.raises(ValueError, match="evidence must contain Evidence values"):
        AgentEvidenceSet(
            tenant_id=tenant_id,
            evidence=("not-evidence",),
        )


def test_agent_evidence_set_requires_evidence_when_execution_needs_it():
    tenant_id = uuid4()
    evidence_set = AgentEvidenceSet(tenant_id=tenant_id)

    with pytest.raises(ValueError, match="execution evidence is required"):
        evidence_set.require()

