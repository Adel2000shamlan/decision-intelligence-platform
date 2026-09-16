from uuid import UUID

from app.modules.pilot.domain.models import (
    Feedback,
    FeedbackType,
    PilotParticipant,
)


class PilotService:
    def __init__(self) -> None:
        self._participants: dict[UUID, PilotParticipant] = {}
        self._feedback: dict[UUID, Feedback] = {}

    def invite(self, tenant_id: UUID, actor_id: UUID) -> PilotParticipant:
        participant = PilotParticipant.invite(tenant_id, actor_id)
        self._participants[participant.id] = participant
        return participant

    def start_onboarding(
        self,
        tenant_id: UUID,
        participant_id: UUID,
    ) -> PilotParticipant:
        participant = self._get_participant(tenant_id, participant_id)
        updated = participant.start_onboarding()
        self._participants[participant_id] = updated
        return updated

    def activate(
        self,
        tenant_id: UUID,
        participant_id: UUID,
    ) -> PilotParticipant:
        participant = self._get_participant(tenant_id, participant_id)
        updated = participant.activate()
        self._participants[participant_id] = updated
        return updated

    def submit_feedback(
        self,
        tenant_id: UUID,
        participant_id: UUID,
        feedback_type: FeedbackType,
        message: str,
    ) -> Feedback:
        participant = self._get_participant(tenant_id, participant_id)
        feedback = Feedback.submit(
            tenant_id,
            participant,
            feedback_type,
            message,
        )
        self._feedback[feedback.id] = feedback
        return feedback

    def participants(self, tenant_id: UUID) -> tuple[PilotParticipant, ...]:
        return tuple(
            item
            for item in self._participants.values()
            if item.tenant_id == tenant_id
        )

    def feedback(self, tenant_id: UUID) -> tuple[Feedback, ...]:
        return tuple(
            item
            for item in self._feedback.values()
            if item.tenant_id == tenant_id
        )

    def _get_participant(
        self,
        tenant_id: UUID,
        participant_id: UUID,
    ) -> PilotParticipant:
        participant = self._participants.get(participant_id)
        if participant is None:
            raise KeyError("pilot participant not found")
        if participant.tenant_id != tenant_id:
            raise PermissionError("participant does not belong to tenant")
        return participant
