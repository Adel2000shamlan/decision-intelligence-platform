from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app"


def test_v108_governance_module_has_policy_and_audit_contracts():
    governance = APP / "modules" / "governance"
    assert (governance / "domain" / "policy.py").is_file()
    assert (governance / "domain" / "audit.py").is_file()


def test_v108_security_middleware_exists():
    assert (APP / "api" / "security.py").is_file()


def test_v108_governance_audit_is_tenant_aware_and_tamper_evident():
    audit = (APP / "modules" / "governance" / "domain" / "audit.py").read_text(
        encoding="utf-8"
    )
    assert "tenant_id" in audit
    assert "correlation_id" in audit
    assert "previous_hash" in audit
    assert "record_hash" in audit


def test_v108_governance_policy_is_fail_closed():
    policy = (APP / "modules" / "governance" / "domain" / "policy.py").read_text(
        encoding="utf-8"
    )
    assert "default_deny" in policy
    assert "fail_closed" in policy


def test_v108_security_middleware_defines_security_headers():
    security = (APP / "api" / "security.py").read_text(encoding="utf-8")
    for header in (
        "Strict-Transport-Security",
        "Content-Security-Policy",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
    ):
        assert header in security


def test_v108_governance_does_not_expose_secrets():
    from uuid import uuid4

    from app.modules.governance.domain.audit import GovernanceAuditLog

    audit = GovernanceAuditLog()
    safe = {"decision": "approved", "reason": "policy"}
    audit.append(
        tenant_id=uuid4(),
        correlation_id=uuid4(),
        action="decision.reviewed",
        payload=safe,
    )

    assert audit.verify()

    try:
        audit.append(
            tenant_id=uuid4(),
            correlation_id=uuid4(),
            action="credential.exposed",
            payload={"password": "should-never-be-recorded"},
        )
    except ValueError:
        pass
    else:
        raise AssertionError("secret payload must be rejected")

def test_v108_security_headers_are_applied_to_fastapi_responses():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.get("/")

    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert response.headers["Content-Security-Policy"] == "default-src 'self'"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"

def test_v108_governance_audit_detects_tampering():
    from dataclasses import replace
    from uuid import uuid4

    from app.modules.governance.domain.audit import GovernanceAuditLog

    audit = GovernanceAuditLog()
    audit.append(
        tenant_id=uuid4(),
        correlation_id=uuid4(),
        action="decision.reviewed",
        actor_id=uuid4(),
        payload={"decision": "approved"},
    )

    assert audit.verify()

    audit.records[0] = replace(
        audit.records[0],
        payload=(("decision", "tampered"),),
    )

    assert not audit.verify()

def test_v108_governance_audit_isolation_between_tenants():
    from uuid import uuid4

    from app.modules.governance.domain.audit import GovernanceAuditLog

    audit = GovernanceAuditLog()
    tenant_a = uuid4()
    tenant_b = uuid4()

    audit.append(
        tenant_id=tenant_a,
        correlation_id=uuid4(),
        action="tenant.a",
        payload={"event": "a"},
    )
    audit.append(
        tenant_id=tenant_b,
        correlation_id=uuid4(),
        action="tenant.b",
        payload={"event": "b"},
    )

    records_a = audit.for_tenant(tenant_a)
    records_b = audit.for_tenant(tenant_b)

    assert len(records_a) == 1
    assert records_a[0].tenant_id == tenant_a
    assert records_a[0].action == "tenant.a"

    assert len(records_b) == 1
    assert records_b[0].tenant_id == tenant_b
    assert records_b[0].action == "tenant.b"

def test_v108_governance_policy_fails_closed_for_invalid_context():
    from uuid import uuid4

    from app.modules.governance.domain.policy import (
        GovernanceContext,
        GovernancePolicy,
    )

    policy = GovernancePolicy()

    valid = GovernanceContext(
        tenant_id=uuid4(),
        actor_id=uuid4(),
        permission="decision.read",
        resource="decision",
        correlation_id=uuid4(),
    )

    decision = policy.evaluate(valid)

    assert decision.allowed is False
    assert decision.policy_id == "governance.default-deny.v1"

    invalid = GovernanceContext(
        tenant_id="invalid-tenant",
        actor_id=uuid4(),
        permission="decision.read",
        resource="decision",
        correlation_id=uuid4(),
    )

    denied = policy.evaluate(invalid)

    assert denied.allowed is False
    assert denied.reason == "tenant context is required"

