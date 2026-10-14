from uuid import uuid4

import pytest

from app.modules.pilot import (
    FeedbackType,
    PilotService,
    PilotStatus,
)


def test_pilot_onboarding_lifecycle():
    service = PilotService()
    tenant = uuid4()
    actor = uuid4()

    participant = service.invite(tenant, actor)
    assert participant.status == PilotStatus.INVITED

    participant = service.start_onboarding(tenant, participant.id)
    assert participant.status == PilotStatus.ONBOARDING

    participant = service.activate(tenant, participant.id)
    assert participant.status == PilotStatus.ACTIVE
    assert participant.activated_at is not None


def test_feedback_requires_active_participant():
    service = PilotService()
    tenant = uuid4()
    participant = service.invite(tenant, uuid4())

    with pytest.raises(ValueError):
        service.submit_feedback(
            tenant,
            participant.id,
            FeedbackType.IDEA,
            "Add a better dashboard",
        )


def test_feedback_is_tenant_scoped():
    service = PilotService()
    tenant_a = uuid4()
    tenant_b = uuid4()

    participant = service.invite(tenant_a, uuid4())
    participant = service.start_onboarding(tenant_a, participant.id)
    participant = service.activate(tenant_a, participant.id)

    with pytest.raises(PermissionError):
        service.submit_feedback(
            tenant_b,
            participant.id,
            FeedbackType.EXPERIENCE,
            "Cross tenant attempt",
        )


def test_active_participant_can_submit_feedback():
    service = PilotService()
    tenant = uuid4()

    participant = service.invite(tenant, uuid4())
    participant = service.start_onboarding(tenant, participant.id)
    participant = service.activate(tenant, participant.id)

    feedback = service.submit_feedback(
        tenant,
        participant.id,
        FeedbackType.IDEA,
        "Improve project analysis",
    )

    assert feedback.tenant_id == tenant
    assert feedback.participant_id == participant.id
    assert feedback.feedback_type == FeedbackType.IDEA
    assert len(service.feedback(tenant)) == 1
