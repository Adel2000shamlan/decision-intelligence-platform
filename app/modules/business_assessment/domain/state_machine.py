from enum import Enum

from app.shared.domain.state_machine import StateMachine, validate_transition_graph


class BusinessAssessmentStatus(str, Enum):
    DRAFT = "draft"
    DATA_COLLECTION = "data_collection"
    UNDER_ANALYSIS = "under_analysis"
    COMPLETED = "completed"
    ARCHIVED = "archived"


BUSINESS_ASSESSMENT_STATE_MACHINE = StateMachine({
    BusinessAssessmentStatus.DRAFT: {
        BusinessAssessmentStatus.DATA_COLLECTION,
        BusinessAssessmentStatus.ARCHIVED,
    },
    BusinessAssessmentStatus.DATA_COLLECTION: {
        BusinessAssessmentStatus.UNDER_ANALYSIS,
        BusinessAssessmentStatus.ARCHIVED,
    },
    BusinessAssessmentStatus.UNDER_ANALYSIS: {
        BusinessAssessmentStatus.COMPLETED,
        BusinessAssessmentStatus.DATA_COLLECTION,
        BusinessAssessmentStatus.ARCHIVED,
    },
    BusinessAssessmentStatus.COMPLETED: {
        BusinessAssessmentStatus.ARCHIVED,
    },
    BusinessAssessmentStatus.ARCHIVED: set(),
}, terminal={BusinessAssessmentStatus.ARCHIVED})

validate_transition_graph(BUSINESS_ASSESSMENT_STATE_MACHINE)
