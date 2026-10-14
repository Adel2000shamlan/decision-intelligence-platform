from __future__ import annotations

from dataclasses import replace
from uuid import NAMESPACE_URL, uuid5

from app.modules.intelligence.application.decision import (
    DecisionIntelligenceInput,
)
from app.modules.intelligence.domain.evidence import Evidence, EvidenceType
from app.modules.learning.domain.feedback import LearningFeedback


class LearningFeedbackIntelligenceAdapter:
    """Converts tenant-scoped learning feedback into traceable observations."""

    def enrich(
        self,
        request: DecisionIntelligenceInput,
        feedback: LearningFeedback,
    ) -> DecisionIntelligenceInput:
        if request.tenant_id != feedback.tenant_id:
            raise ValueError("feedback tenant_id does not match request")

        evidence = self._to_evidence(feedback)
        return replace(request, evidence=request.evidence + (evidence,))

    @staticmethod
    def _to_evidence(feedback: LearningFeedback) -> Evidence:
        observation_ids = tuple(
            sorted(str(item.id) for item in feedback.observations)
        )
        source_event_ids = tuple(
            sorted(
                {
                    str(item.source_event_id)
                    for item in feedback.observations
                    if item.source_event_id is not None
                }
            )
        )

        reference = (
            f"learning-feedback:{feedback.tenant_id}:{feedback.metric}:"
            f"{','.join(observation_ids) if observation_ids else 'empty'}"
        )

        statement_parts = [
            f"Historical learning feedback for metric '{feedback.metric}' "
            f"contains {feedback.observation_count} observation(s).",
            (
                f"Outcomes: success={feedback.success_count}, "
                f"partial={feedback.partial_count}, "
                f"failure={feedback.failure_count}, "
                f"unknown={feedback.unknown_count}."
            ),
        ]

        if feedback.average_variance is not None:
            statement_parts.append(
                f"Average variance={feedback.average_variance:.6g}."
            )

        if feedback.average_confidence is not None:
            statement_parts.append(
                f"Average observation confidence="
                f"{feedback.average_confidence:.6g}."
            )

        statement_parts.append(
            "Source observation IDs: "
            + (", ".join(observation_ids) if observation_ids else "none")
            + "."
        )
        statement_parts.append(
            "Source event IDs: "
            + (", ".join(source_event_ids) if source_event_ids else "none")
            + "."
        )

        return Evidence(
            evidence_id=uuid5(NAMESPACE_URL, reference),
            tenant_id=feedback.tenant_id,
            evidence_type=EvidenceType.OBSERVATION,
            source="learning-feedback",
            reference=reference,
            statement=" ".join(statement_parts),
            traceable=True,
        )
