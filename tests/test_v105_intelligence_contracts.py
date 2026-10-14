from uuid import uuid4

import pytest

from app.modules.intelligence.domain.confidence import Confidence
from app.modules.intelligence.domain.evidence import Evidence, EvidenceType
from app.modules.intelligence.domain.result import IntelligenceResult
from app.modules.intelligence.domain.scoring import (
    DeterministicScoringEngine,
    ScoreFactor,
)


def test_evidence_contract_requires_traceable_source():
    evidence = Evidence(
        evidence_id=uuid4(),
        tenant_id=uuid4(),
        evidence_type=EvidenceType.SOURCE,
        source="market-research",
        reference="source-001",
        statement="Observed customer demand",
    )

    assert evidence.traceable is True
    assert evidence.evidence_type is EvidenceType.SOURCE


def test_evidence_contract_rejects_empty_source():
    with pytest.raises(ValueError, match="source is required"):
        Evidence(
            evidence_id=uuid4(),
            tenant_id=uuid4(),
            evidence_type=EvidenceType.FACT,
            source="",
            reference="source-001",
            statement="Known fact",
        )


def test_confidence_is_distinct_from_probability():
    confidence = Confidence(
        value=0.82,
        basis="three independent verified sources",
    )

    assert confidence.value == 0.82
    assert confidence.basis == "three independent verified sources"


def test_confidence_rejects_out_of_range_value():
    with pytest.raises(ValueError, match="between 0 and 1"):
        Confidence(
            value=1.2,
            basis="invalid",
        )


def test_intelligence_result_separates_facts_assumptions_and_estimates():
    tenant_id = uuid4()
    actor_id = uuid4()
    correlation_id = uuid4()

    evidence = Evidence(
        evidence_id=uuid4(),
        tenant_id=tenant_id,
        evidence_type=EvidenceType.FACT,
        source="verified-data",
        reference="data-001",
        statement="Confirmed operating cost",
    )

    result = IntelligenceResult(
        tenant_id=tenant_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        result={"recommendation": "review"},
        evidence=(evidence,),
        confidence=Confidence(
            value=0.9,
            basis="verified evidence",
        ),
        confirmed_facts=("Operating cost is confirmed",),
        assumptions=("Demand remains stable",),
        estimates=("Expected monthly revenue",),
    )

    assert result.confirmed_facts == ("Operating cost is confirmed",)
    assert result.assumptions == ("Demand remains stable",)
    assert result.estimates == ("Expected monthly revenue",)
    assert result.human_review_required is True


def test_deterministic_scoring_is_reproducible():
    factors = (
        ScoreFactor("market", 0.8, 2.0),
        ScoreFactor("finance", 0.6, 1.0),
        ScoreFactor("risk", 0.4, 1.0),
    )

    engine = DeterministicScoringEngine()

    first = engine.calculate(factors)
    second = engine.calculate(factors)

    assert first.value == second.value
    assert first.factors == second.factors
    assert first.value == pytest.approx(0.65)


def test_deterministic_scoring_rejects_zero_total_weight():
    factors = (
        ScoreFactor("market", 0.8, 0.0),
        ScoreFactor("finance", 0.6, 0.0),
    )

    with pytest.raises(
        ValueError,
        match="total score weight must be greater than zero",
    ):
        DeterministicScoringEngine().calculate(factors)


def test_human_approval_gate_delegates_to_existing_authorization():
    from app.modules.identity.domain.security_identity import (
        ActorContext,
        SecurityIdentity,
    )
    from app.modules.authorization.domain.models import (
        Action,
        AuthorizationContext,
        Permission,
        Resource,
        ResourceType,
    )

    tenant_id = uuid4()
    user_id = uuid4()
    authentication_id = uuid4()
    correlation_id = uuid4()
    decision_id = uuid4()

    identity = SecurityIdentity(
        user_id=user_id,
        authentication_id=authentication_id,
        assurance_level="strong",
        authenticated=True,
    )

    actor = ActorContext(
        actor_id=user_id,
        authentication_id=authentication_id,
        correlation_id=correlation_id,
        actor_type="human",
        authenticated=True,
    )

    context = AuthorizationContext(
        identity=identity,
        actor=actor,
        tenant_id=tenant_id,
        permission=Permission(ResourceType.DECISION, Action.APPROVE),
        resource=Resource(
            ResourceType.DECISION,
            decision_id,
            tenant_id,
        ),
        correlation_id=correlation_id,
    )

    from app.modules.intelligence.application.approval import HumanApprovalGate

    result = HumanApprovalGate().evaluate(context)

    assert result.approved is True
    assert result.policy_id == "auth.human-approval.v1"
    assert result.correlation_id == correlation_id


def test_human_approval_gate_rejects_ai():
    from app.modules.identity.domain.security_identity import (
        ActorContext,
        SecurityIdentity,
    )
    from app.modules.authorization.domain.models import (
        Action,
        AuthorizationContext,
        Permission,
        Resource,
        ResourceType,
    )
    from app.modules.intelligence.application.approval import HumanApprovalGate

    tenant_id = uuid4()
    actor_id = uuid4()
    authentication_id = uuid4()
    correlation_id = uuid4()

    identity = SecurityIdentity(
        user_id=actor_id,
        authentication_id=authentication_id,
        assurance_level="strong",
        authenticated=True,
    )

    actor = ActorContext(
        actor_id=actor_id,
        authentication_id=authentication_id,
        correlation_id=correlation_id,
        actor_type="ai",
        authenticated=True,
    )

    context = AuthorizationContext(
        identity=identity,
        actor=actor,
        tenant_id=tenant_id,
        permission=Permission(ResourceType.DECISION, Action.APPROVE),
        resource=Resource(
            ResourceType.DECISION,
            uuid4(),
            tenant_id,
        ),
        correlation_id=correlation_id,
    )

    result = HumanApprovalGate().evaluate(context)

    assert result.approved is False
    assert "human" in result.reason.lower()


def test_decision_intelligence_service_produces_structured_result():
    from app.modules.intelligence.application.decision import (
        DecisionIntelligenceInput,
        DecisionIntelligenceService,
    )
    from app.modules.intelligence.domain.evidence import Evidence, EvidenceType
    from app.modules.intelligence.domain.scoring import ScoreFactor

    tenant_id = uuid4()
    actor_id = uuid4()
    correlation_id = uuid4()

    evidence = Evidence(
        evidence_id=uuid4(),
        tenant_id=tenant_id,
        evidence_type=EvidenceType.FACT,
        source="customer-survey",
        reference="survey-001",
        statement="Customers reported demand.",
    )

    request = DecisionIntelligenceInput(
        tenant_id=tenant_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        evidence=(evidence,),
        factors=(
            ScoreFactor("market", 0.8, 1.0),
            ScoreFactor("finance", 0.6, 1.0),
        ),
        confirmed_facts=("Customer demand was observed.",),
        assumptions=("Demand will remain stable.",),
        estimates=("Expected monthly revenue is estimated.",),
    )

    result = DecisionIntelligenceService().analyze(request)

    assert result.tenant_id == tenant_id
    assert result.actor_id == actor_id
    assert result.correlation_id == correlation_id
    assert result.result.value == 0.7
    assert result.evidence == (evidence,)
    assert result.confirmed_facts == ("Customer demand was observed.",)
    assert result.assumptions == ("Demand will remain stable.",)
    assert result.estimates == ("Expected monthly revenue is estimated.",)
    assert result.human_review_required is True
    assert result.confidence.value == 0.0


def test_decision_intelligence_service_is_reproducible():
    from app.modules.intelligence.application.decision import (
        DecisionIntelligenceInput,
        DecisionIntelligenceService,
    )
    from app.modules.intelligence.domain.evidence import Evidence, EvidenceType
    from app.modules.intelligence.domain.scoring import ScoreFactor

    tenant_id = uuid4()
    actor_id = uuid4()
    correlation_id = uuid4()

    evidence = Evidence(
        evidence_id=uuid4(),
        tenant_id=tenant_id,
        evidence_type=EvidenceType.SOURCE,
        source="official-source",
        reference="source-001",
        statement="Verified market information.",
    )

    request = DecisionIntelligenceInput(
        tenant_id=tenant_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        evidence=(evidence,),
        factors=(ScoreFactor("market", 0.9, 2.0),),
        confirmed_facts=("Verified fact.",),
    )

    service = DecisionIntelligenceService()
    first = service.analyze(request)
    second = service.analyze(request)

    assert first.result == second.result
    assert first.confidence == second.confidence
    assert first.confirmed_facts == second.confirmed_facts


def test_scenario_intelligence_service_produces_structured_result():
    from app.modules.intelligence.application.scenario import (
        ScenarioIntelligenceInput,
        ScenarioIntelligenceService,
    )
    from app.modules.intelligence.domain.evidence import Evidence, EvidenceType
    from app.modules.intelligence.domain.scoring import ScoreFactor

    tenant_id = uuid4()
    actor_id = uuid4()
    correlation_id = uuid4()

    evidence = Evidence(
        evidence_id=uuid4(),
        tenant_id=tenant_id,
        evidence_type=EvidenceType.OBSERVATION,
        source="scenario-analysis",
        reference="scenario-001",
        statement="Observed demand supports the base scenario.",
    )

    request = ScenarioIntelligenceInput(
        tenant_id=tenant_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        evidence=(evidence,),
        factors=(
            ScoreFactor("demand", 0.9, 2.0),
            ScoreFactor("cost", 0.7, 1.0),
        ),
        confirmed_facts=("Observed demand supports the scenario.",),
        assumptions=("Demand remains stable.",),
        estimates=("Future revenue is estimated.",),
    )

    result = ScenarioIntelligenceService().analyze(request)

    assert result.tenant_id == tenant_id
    assert result.actor_id == actor_id
    assert result.correlation_id == correlation_id
    assert result.result.value == (0.9 * 2.0 + 0.7) / 3.0
    assert result.evidence == (evidence,)
    assert result.confirmed_facts == (
        "Observed demand supports the scenario.",
    )
    assert result.assumptions == ("Demand remains stable.",)
    assert result.estimates == ("Future revenue is estimated.",)
    assert result.human_review_required is True


def test_scenario_intelligence_requires_evidence():
    from app.modules.intelligence.application.scenario import (
        ScenarioIntelligenceInput,
    )
    from app.modules.intelligence.domain.scoring import ScoreFactor

    try:
        ScenarioIntelligenceInput(
            tenant_id=uuid4(),
            actor_id=uuid4(),
            correlation_id=uuid4(),
            evidence=(),
            factors=(ScoreFactor("demand", 0.8, 1.0),),
            confirmed_facts=("Fact.",),
        )
    except ValueError as exc:
        assert str(exc) == "at least one evidence item is required"
    else:
        raise AssertionError("expected ValueError")


def test_risk_intelligence_service_produces_structured_result():
    from app.modules.intelligence.application.risk import (
        RiskIntelligenceInput,
        RiskIntelligenceService,
    )
    from app.modules.intelligence.domain.evidence import Evidence, EvidenceType
    from app.modules.intelligence.domain.scoring import ScoreFactor

    tenant_id = uuid4()
    actor_id = uuid4()
    correlation_id = uuid4()

    evidence = Evidence(
        evidence_id=uuid4(),
        tenant_id=tenant_id,
        evidence_type=EvidenceType.SOURCE,
        source="risk-register",
        reference="risk-001",
        statement="Operational dependency was identified.",
    )

    request = RiskIntelligenceInput(
        tenant_id=tenant_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        evidence=(evidence,),
        factors=(
            ScoreFactor("probability", 0.8, 2.0),
            ScoreFactor("impact", 0.6, 1.0),
        ),
        confirmed_facts=("Operational dependency was identified.",),
        assumptions=("Dependency remains available.",),
        estimates=("Potential loss is estimated.",),
    )

    result = RiskIntelligenceService().analyze(request)

    assert result.tenant_id == tenant_id
    assert result.actor_id == actor_id
    assert result.correlation_id == correlation_id
    assert result.result.value == (0.8 * 2.0 + 0.6) / 3.0
    assert result.evidence == (evidence,)
    assert result.confirmed_facts == (
        "Operational dependency was identified.",
    )
    assert result.assumptions == ("Dependency remains available.",)
    assert result.estimates == ("Potential loss is estimated.",)
    assert result.human_review_required is True


def test_risk_intelligence_requires_evidence():
    from app.modules.intelligence.application.risk import (
        RiskIntelligenceInput,
    )
    from app.modules.intelligence.domain.scoring import ScoreFactor

    try:
        RiskIntelligenceInput(
            tenant_id=uuid4(),
            actor_id=uuid4(),
            correlation_id=uuid4(),
            evidence=(),
            factors=(ScoreFactor("impact", 0.8, 1.0),),
            confirmed_facts=("Risk identified.",),
        )
    except ValueError as exc:
        assert str(exc) == "at least one evidence item is required"
    else:
        raise AssertionError("expected ValueError")


def test_intelligence_gateway_routes_model_and_prompt():
    from app.modules.intelligence.application.gateway import (
        IntelligenceGatewayService,
    )
    from app.modules.intelligence.domain.prompt_registry import (
        PromptDefinition,
    )

    tenant_id = uuid4()
    actor_id = uuid4()
    correlation_id = uuid4()

    service = IntelligenceGatewayService()

    service.prompts.register(
        PromptDefinition(
            task="decision",
            version="v1",
            template="Analyze the decision using supplied evidence.",
        )
    )

    result = service.generate(
        tenant_id=tenant_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        task="decision",
        prompt_version="v1",
    )

    assert result.request_id is not None
    assert result.model == "default-decision"
    assert result.provider == "local"
    assert result.prompt_version == "v1"
    assert result.output == {
        "task": "decision",
        "status": "gateway-accepted",
    }


def test_intelligence_gateway_rejects_unregistered_prompt():
    from app.modules.intelligence.application.gateway import (
        IntelligenceGatewayService,
    )

    service = IntelligenceGatewayService()

    try:
        service.generate(
            tenant_id=uuid4(),
            actor_id=uuid4(),
            correlation_id=uuid4(),
            task="risk",
            prompt_version="missing",
        )
    except ValueError as exc:
        assert str(exc) == (
            "prompt version not registered: risk:missing"
        )
    else:
        raise AssertionError("expected ValueError")


def test_intelligence_gateway_rejects_unsupported_task():
    from app.modules.intelligence.application.gateway import (
        IntelligenceGatewayService,
    )

    service = IntelligenceGatewayService()

    try:
        service.generate(
            tenant_id=uuid4(),
            actor_id=uuid4(),
            correlation_id=uuid4(),
            task="unknown",
            prompt_version="v1",
        )
    except ValueError as exc:
        assert str(exc) == "unsupported intelligence task: unknown"
    else:
        raise AssertionError("expected ValueError")


def test_intelligence_analysis_coordinator_keeps_analysis_separate_from_approval():
    from app.modules.intelligence.application.analysis import (
        IntelligenceAnalysisService,
    )
    from app.modules.intelligence.application.decision import (
        DecisionIntelligenceInput,
    )
    from app.modules.intelligence.domain.evidence import Evidence, EvidenceType
    from app.modules.intelligence.domain.scoring import ScoreFactor

    tenant_id = uuid4()
    actor_id = uuid4()
    correlation_id = uuid4()

    evidence = Evidence(
        evidence_id=uuid4(),
        tenant_id=tenant_id,
        evidence_type=EvidenceType.FACT,
        source="verified-source",
        reference="decision-001",
        statement="Verified market fact.",
    )

    request = DecisionIntelligenceInput(
        tenant_id=tenant_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        evidence=(evidence,),
        factors=(ScoreFactor("market", 0.8, 1.0),),
        confirmed_facts=("Verified market fact.",),
    )

    result = IntelligenceAnalysisService().analyze_decision(request)

    assert result.analysis.result.value == 0.8
    assert result.analysis.human_review_required is True
    assert result.approval is None
    assert result.approval_context_present is False


def test_intelligence_analysis_coordinator_rejects_ai_approval_context():
    from app.modules.authorization.domain.models import (
        Action,
        AuthorizationContext,
        Permission,
        Resource,
        ResourceType,
    )
    from app.modules.identity.domain.security_identity import (
        ActorContext,
        SecurityIdentity,
    )
    from app.modules.intelligence.application.analysis import (
        IntelligenceAnalysisService,
    )
    from app.modules.intelligence.application.decision import (
        DecisionIntelligenceInput,
    )
    from app.modules.intelligence.domain.evidence import Evidence, EvidenceType
    from app.modules.intelligence.domain.scoring import ScoreFactor

    tenant_id = uuid4()
    actor_id = uuid4()
    authentication_id = uuid4()
    correlation_id = uuid4()

    evidence = Evidence(
        evidence_id=uuid4(),
        tenant_id=tenant_id,
        evidence_type=EvidenceType.FACT,
        source="verified-source",
        reference="decision-002",
        statement="Verified fact.",
    )

    request = DecisionIntelligenceInput(
        tenant_id=tenant_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        evidence=(evidence,),
        factors=(ScoreFactor("market", 0.9, 1.0),),
        confirmed_facts=("Verified fact.",),
    )

    analysis_service = IntelligenceAnalysisService()
    analysis = analysis_service.analyze_decision(request)

    identity = SecurityIdentity(
        user_id=actor_id,
        authentication_id=authentication_id,
        assurance_level="strong",
        authenticated=True,
    )

    actor = ActorContext(
        actor_id=actor_id,
        authentication_id=authentication_id,
        correlation_id=correlation_id,
        actor_type="ai",
        authenticated=True,
    )

    context = AuthorizationContext(
        identity=identity,
        actor=actor,
        tenant_id=tenant_id,
        permission=Permission(ResourceType.DECISION, Action.APPROVE),
        resource=Resource(
            ResourceType.DECISION,
            uuid4(),
            tenant_id,
        ),
        correlation_id=correlation_id,
    )

    result = analysis_service.evaluate_approval(analysis, context)

    assert result.approval is not None
    assert result.approval.approved is False
    assert result.approval_context_present is True


def test_intelligence_application_service_exposes_public_boundary():
    from app.modules.intelligence.application.service import (
        IntelligenceApplicationService,
    )
    from app.modules.intelligence.application.decision import (
        DecisionIntelligenceInput,
    )
    from app.modules.intelligence.application.scenario import (
        ScenarioIntelligenceInput,
    )
    from app.modules.intelligence.application.risk import (
        RiskIntelligenceInput,
    )
    from app.modules.intelligence.domain.evidence import Evidence, EvidenceType
    from app.modules.intelligence.domain.scoring import ScoreFactor

    tenant_id = uuid4()
    actor_id = uuid4()
    correlation_id = uuid4()

    evidence = Evidence(
        evidence_id=uuid4(),
        tenant_id=tenant_id,
        evidence_type=EvidenceType.FACT,
        source="integration-test",
        reference="v105-boundary",
        statement="Verified intelligence input.",
    )

    factors = (ScoreFactor("quality", 0.8, 1.0),)
    facts = ("Verified intelligence input.",)

    service = IntelligenceApplicationService()

    decision = service.analyze_decision(
        DecisionIntelligenceInput(
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            evidence=(evidence,),
            factors=factors,
            confirmed_facts=facts,
        )
    )

    scenario = service.analyze_scenario(
        ScenarioIntelligenceInput(
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            evidence=(evidence,),
            factors=factors,
            confirmed_facts=facts,
        )
    )

    risk = service.analyze_risk(
        RiskIntelligenceInput(
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            evidence=(evidence,),
            factors=factors,
            confirmed_facts=facts,
        )
    )

    assert decision.analysis.result.value == 0.8
    assert scenario.analysis.result.value == 0.8
    assert risk.analysis.result.value == 0.8

    assert decision.analysis.human_review_required is True
    assert scenario.analysis.human_review_required is True
    assert risk.analysis.human_review_required is True
