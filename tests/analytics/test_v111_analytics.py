from uuid import uuid4

import pytest

from app.modules.analytics import (
    AnalyticsEvent,
    AnalyticsService,
    DEFAULT_MVP_KPIS,
    KPIMeasurement,
)


def test_event_recording_is_tenant_scoped():
    service = AnalyticsService()
    tenant_a = uuid4()
    tenant_b = uuid4()

    service.record(AnalyticsEvent.create(tenant_a, "onboarding.started"))
    service.record(AnalyticsEvent.create(tenant_a, "onboarding.completed"))
    service.record(AnalyticsEvent.create(tenant_b, "onboarding.started"))

    assert service.summary(tenant_a) == {
        "onboarding.started": 1,
        "onboarding.completed": 1,
    }
    assert len(service.events(tenant_b)) == 1


def test_measurements_are_tenant_scoped():
    service = AnalyticsService()
    tenant_a = uuid4()
    tenant_b = uuid4()

    service.measure(KPIMeasurement.create("weekly_active_pilot_users", 7, tenant_a))
    service.measure(KPIMeasurement.create("weekly_active_pilot_users", 99, tenant_b))

    assert len(service.measurements(tenant_a)) == 1
    assert service.measurements(tenant_a)[0].value == 7


def test_default_mvp_kpis_are_defined():
    names = {kpi.name for kpi in DEFAULT_MVP_KPIS}

    assert {
        "pilot_onboarding_completion_rate",
        "weekly_active_pilot_users",
        "feedback_submission_rate",
        "support_first_response_minutes",
        "critical_incident_rate",
    } <= names


def test_empty_event_name_rejected():
    with pytest.raises(ValueError):
        AnalyticsEvent.create(uuid4(), "   ")
