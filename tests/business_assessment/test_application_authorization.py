from uuid import uuid4

import pytest

from app.modules.business_assessment.application.authorization import (
    BusinessAssessmentAuthorizationAdapter,
    BusinessAssessmentAuthorizationError,
)


def test_requires_authenticated_actor():
    authorization = BusinessAssessmentAuthorizationAdapter()

    with pytest.raises(BusinessAssessmentAuthorizationError):
        authorization.require(
            "create",
            None,
            uuid4(),
        )


def test_requires_tenant_context():
    authorization = BusinessAssessmentAuthorizationAdapter()

    with pytest.raises(BusinessAssessmentAuthorizationError):
        authorization.require(
            "create",
            uuid4(),
            None,
        )


def test_allows_action_when_permission_is_allowed():
    authorization = BusinessAssessmentAuthorizationAdapter(
        {"business_assessment:create"}
    )

    authorization.require(
        "create",
        uuid4(),
        uuid4(),
    )


def test_rejects_action_when_permission_is_missing():
    authorization = BusinessAssessmentAuthorizationAdapter(
        {"business_assessment:update"}
    )

    with pytest.raises(BusinessAssessmentAuthorizationError):
        authorization.require(
            "create",
            uuid4(),
            uuid4(),
        )


def test_empty_permissions_allow_authenticated_tenant():
    authorization = BusinessAssessmentAuthorizationAdapter()

    authorization.require(
        "create",
        uuid4(),
        uuid4(),
    )
