from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class PilotStatus(str, Enum):
    INVITED = "invited"
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    COMPLETED = "completed"
    WITHDRAWN = "withdrawn"


class FeedbackType(str, Enum):
    BUG = "bug"
    IDEA = "idea"
    QUESTION = "question"
    EXPERIENCE = "experience"


@dataclass(frozen=True, slots=True)
class PilotParticipant:
    id: UUID
    tenant_id: UUID
    actor_id: UUID
    status: PilotStatus
    invited_at: datetime
    activated_at: datetime | None = None

    @classmethod
    def invite(cls, tenant_id: UUID, actor_id: UUID) -> "PilotParticipant":
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            actor_id=actor_id,
            status=PilotStatus.INVITED,
            invited_at=datetime.now(timezone.utc),
        )

    def start_onboarding(self) -> "PilotParticipant":
        if self.status != PilotStatus.INVITED:
            raise ValueError("pilot participant must be invited before onboarding")
        return PilotParticipant(
            id=self.id,
            tenant_id=self.tenant_id,
            actor_id=self.actor_id,
            status=PilotStatus.ONBOARDING,
            invited_at=self.invited_at,
            activated_at=self.activated_at,
        )

    def activate(self) -> "PilotParticipant":
        if self.status != PilotStatus.ONBOARDING:
            raise ValueError("pilot participant must complete onboarding before activation")
        return PilotParticipant(
            id=self.id,
            tenant_id=self.tenant_id,
            actor_id=self.actor_id,
            status=PilotStatus.ACTIVE,
            invited_at=self.invited_at,
            activated_at=datetime.now(timezone.utc),
        )


@dataclass(frozen=True, slots=True)
class Feedback:
    id: UUID
    tenant_id: UUID
    participant_id: UUID
    actor_id: UUID
    feedback_type: FeedbackType
    message: str
    created_at: datetime
    resolved: bool = False

    @classmethod
    def submit(
        cls,
        tenant_id: UUID,
        participant: PilotParticipant,
        feedback_type: FeedbackType,
        message: str,
    ) -> "Feedback":
        if participant.tenant_id != tenant_id:
            raise PermissionError("participant does not belong to tenant")
        if participant.status != PilotStatus.ACTIVE:
            raise ValueError("feedback requires an active pilot participant")
        if not message.strip():
            raise ValueError("feedback message must not be empty")

        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            participant_id=participant.id,
            actor_id=participant.actor_id,
            feedback_type=feedback_type,
            message=message.strip(),
            created_at=datetime.now(timezone.utc),
        )
