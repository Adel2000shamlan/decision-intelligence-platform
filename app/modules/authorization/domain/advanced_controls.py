from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import UUID, uuid4

class ControlViolation(Exception): pass

@dataclass(frozen=True, slots=True)
class ControlResult:
    stage: int
    name: str
    allowed: bool
    reason: str
    obligations: tuple[str,...]=()
    policy_version: str='v1'

@dataclass(frozen=True, slots=True)
class ControlContext:
    actor_id: UUID
    tenant_id: UUID
    action: str
    resource_type: str
    resource_id: UUID
    actor_type: str='human'
    authenticated: bool=True
    assurance: str='strong'
    permission_granted: bool=True
    requester_id: UUID|None=None
    approval_actor_id: UUID|None=None
    risk_score: int=0
    attributes: Mapping[str,Any]=field(default_factory=dict)
    correlation_id: UUID=field(default_factory=uuid4)
    request_id: UUID=field(default_factory=uuid4)
    policy_version: str='v1'
    evaluated_at: datetime=field(default_factory=lambda: datetime.now(timezone.utc))

SENSITIVE={'approve','reject','execute','archive','delete'}

def evaluate_control(stage:int,name:str,ctx:ControlContext,deny=False,reason='control satisfied',obligations=()):
    return ControlResult(stage,name,not deny,reason,tuple(obligations))

def control_11(ctx: ControlContext) -> ControlResult:
    """reject malformed or contradictory authorization contexts."""
    if ctx.actor_id is None or ctx.tenant_id is None: return evaluate_control(11, 'Authorization Boundary & Abuse Tests', ctx, True, 'Authorization Boundary & Abuse Tests'+" failed")
    return evaluate_control(11, 'Authorization Boundary & Abuse Tests', ctx, False, 'reject malformed or contradictory authorization contexts')

def control_12(ctx: ControlContext) -> ControlResult:
    """deny action elevation without explicit permission."""
    if ctx.action in SENSITIVE and not ctx.permission_granted: return evaluate_control(12, 'Privilege Escalation Prevention', ctx, True, 'Privilege Escalation Prevention'+" failed")
    return evaluate_control(12, 'Privilege Escalation Prevention', ctx, False, 'deny action elevation without explicit permission')

def control_13(ctx: ControlContext) -> ControlResult:
    """prevent conflicting duties in one actor context."""
    if ctx.attributes.get("conflicting_duty",False): return evaluate_control(13, 'Separation of Duties', ctx, True, 'Separation of Duties'+" failed")
    return evaluate_control(13, 'Separation of Duties', ctx, False, 'prevent conflicting duties in one actor context')

def control_14(ctx: ControlContext) -> ControlResult:
    """require the minimum requested action scope."""
    if ctx.attributes.get("overbroad_scope",False): return evaluate_control(14, 'Least Privilege Enforcement', ctx, True, 'Least Privilege Enforcement'+" failed")
    return evaluate_control(14, 'Least Privilege Enforcement', ctx, False, 'require the minimum requested action scope')

def control_15(ctx: ControlContext) -> ControlResult:
    """deny cannot be overridden by later allow."""
    if ctx.attributes.get("deny_override",False): return evaluate_control(15, 'Deny Override Protection', ctx, True, 'Deny Override Protection'+" failed")
    return evaluate_control(15, 'Deny Override Protection', ctx, False, 'deny cannot be overridden by later allow')

def control_16(ctx: ControlContext) -> ControlResult:
    """support explicit delegated authority."""
    if ctx.attributes.get("delegated",False) and not ctx.attributes.get("delegation_valid",False): return evaluate_control(16, 'Delegated Authorization', ctx, True, 'Delegated Authorization'+" failed")
    return evaluate_control(16, 'Delegated Authorization', ctx, False, 'support explicit delegated authority')

def control_17(ctx: ControlContext) -> ControlResult:
    """expire delegated authority deterministically."""
    if ctx.attributes.get("delegated",False) and ctx.attributes.get("delegation_expired",False): return evaluate_control(17, 'Delegation Expiry', ctx, True, 'Delegation Expiry'+" failed")
    return evaluate_control(17, 'Delegation Expiry', ctx, False, 'expire delegated authority deterministically')

def control_18(ctx: ControlContext) -> ControlResult:
    """requester cannot approve own sensitive request."""
    if ctx.action in {"approve","reject"} and ctx.requester_id is not None and ctx.requester_id==ctx.actor_id: return evaluate_control(18, 'Approval Separation', ctx, True, 'Approval Separation'+" failed")
    return evaluate_control(18, 'Approval Separation', ctx, False, 'requester cannot approve own sensitive request')

def control_19(ctx: ControlContext) -> ControlResult:
    """require two distinct human actors for designated approvals."""
    if ctx.action in {"approve","reject"} and ctx.approval_actor_id is not None and ctx.approval_actor_id==ctx.actor_id: return evaluate_control(19, 'Four Eyes Control', ctx, True, 'Four Eyes Control'+" failed")
    return evaluate_control(19, 'Four Eyes Control', ctx, False, 'require two distinct human actors for designated approvals')

def control_20(ctx: ControlContext) -> ControlResult:
    """inherit scoped access only from approved parent hierarchy."""
    if ctx.attributes.get("invalid_parent_scope",False): return evaluate_control(20, 'Resource Hierarchy Authorization', ctx, True, 'Resource Hierarchy Authorization'+" failed")
    return evaluate_control(20, 'Resource Hierarchy Authorization', ctx, False, 'inherit scoped access only from approved parent hierarchy')

def control_21(ctx: ControlContext) -> ControlResult:
    """enforce owner constraints on protected mutation."""
    if ctx.attributes.get("owner_required",False) and ctx.attributes.get("owner_id") not in (None,ctx.actor_id): return evaluate_control(21, 'Ownership Boundary', ctx, True, 'Ownership Boundary'+" failed")
    return evaluate_control(21, 'Ownership Boundary', ctx, False, 'enforce owner constraints on protected mutation')

def control_22(ctx: ControlContext) -> ControlResult:
    """bind actor, identity and resource to one tenant."""
    if ctx.attributes.get("tenant_mismatch",False): return evaluate_control(22, 'Tenant Isolation Hardening', ctx, True, 'Tenant Isolation Hardening'+" failed")
    return evaluate_control(22, 'Tenant Isolation Hardening', ctx, False, 'bind actor, identity and resource to one tenant')

def control_23(ctx: ControlContext) -> ControlResult:
    """fail closed on cross-tenant access."""
    if ctx.attributes.get("cross_tenant",False): return evaluate_control(23, 'Cross Tenant Denial', ctx, True, 'Cross Tenant Denial'+" failed")
    return evaluate_control(23, 'Cross Tenant Denial', ctx, False, 'fail closed on cross-tenant access')

def control_24(ctx: ControlContext) -> ControlResult:
    """allow only inside an explicit time window."""
    if ctx.attributes.get("outside_window",False): return evaluate_control(24, 'Temporal Authorization', ctx, True, 'Temporal Authorization'+" failed")
    return evaluate_control(24, 'Temporal Authorization', ctx, False, 'allow only inside an explicit time window')

def control_25(ctx: ControlContext) -> ControlResult:
    """validate authorization attributes before policy evaluation."""
    if ctx.attributes.get("untrusted_attribute",False): return evaluate_control(25, 'Context Attribute Integrity', ctx, True, 'Context Attribute Integrity'+" failed")
    return evaluate_control(25, 'Context Attribute Integrity', ctx, False, 'validate authorization attributes before policy evaluation')

def control_26(ctx: ControlContext) -> ControlResult:
    """enforce assurance level for sensitive actions."""
    if ctx.action in SENSITIVE and ctx.assurance!="strong": return evaluate_control(26, 'Session Assurance Enforcement', ctx, True, 'Session Assurance Enforcement'+" failed")
    return evaluate_control(26, 'Session Assurance Enforcement', ctx, False, 'enforce assurance level for sensitive actions')

def control_27(ctx: ControlContext) -> ControlResult:
    """require stronger assurance when policy demands it."""
    if ctx.attributes.get("step_up_required",False) and ctx.assurance!="strong": return evaluate_control(27, 'Step Up Authorization', ctx, True, 'Step Up Authorization'+" failed")
    return evaluate_control(27, 'Step Up Authorization', ctx, False, 'require stronger assurance when policy demands it')

def control_28(ctx: ControlContext) -> ControlResult:
    """require recent authentication for high-risk operations."""
    if ctx.attributes.get("reauth_required",False) and not ctx.attributes.get("recent_auth",False): return evaluate_control(28, 'Reauthentication Boundary', ctx, True, 'Reauthentication Boundary'+" failed")
    return evaluate_control(28, 'Reauthentication Boundary', ctx, False, 'require recent authentication for high-risk operations')

def control_29(ctx: ControlContext) -> ControlResult:
    """deny revoked authentication sessions."""
    if ctx.attributes.get("token_revoked",False): return evaluate_control(29, 'Token Revocation Enforcement', ctx, True, 'Token Revocation Enforcement'+" failed")
    return evaluate_control(29, 'Token Revocation Enforcement', ctx, False, 'deny revoked authentication sessions')

def control_30(ctx: ControlContext) -> ControlResult:
    """deny inactive or revoked credentials."""
    if ctx.attributes.get("credential_inactive",False): return evaluate_control(30, 'Credential State Enforcement', ctx, True, 'Credential State Enforcement'+" failed")
    return evaluate_control(30, 'Credential State Enforcement', ctx, False, 'deny inactive or revoked credentials')

def control_31(ctx: ControlContext) -> ControlResult:
    """constrain emergency access to explicit allowlists."""
    if ctx.attributes.get("emergency",False) and not ctx.attributes.get("emergency_allowed",False): return evaluate_control(31, 'Emergency Access Boundary', ctx, True, 'Emergency Access Boundary'+" failed")
    return evaluate_control(31, 'Emergency Access Boundary', ctx, False, 'constrain emergency access to explicit allowlists')

def control_32(ctx: ControlContext) -> ControlResult:
    """make emergency authorization auditable."""
    if ctx.attributes.get("emergency",False) and not ctx.attributes.get("audit_emitted",False): return evaluate_control(32, 'Emergency Access Audit', ctx, True, 'Emergency Access Audit'+" failed")
    return evaluate_control(32, 'Emergency Access Audit', ctx, False, 'make emergency authorization auditable')

def control_33(ctx: ControlContext) -> ControlResult:
    """require explicit policy versions."""
    if not ctx.policy_version: return evaluate_control(33, 'Policy Versioning', ctx, True, 'Policy Versioning'+" failed")
    return evaluate_control(33, 'Policy Versioning', ctx, False, 'require explicit policy versions')

def control_34(ctx: ControlContext) -> ControlResult:
    """detect contradictory policy outcomes."""
    if ctx.attributes.get("policy_conflict",False): return evaluate_control(34, 'Policy Conflict Detection', ctx, True, 'Policy Conflict Detection'+" failed")
    return evaluate_control(34, 'Policy Conflict Detection', ctx, False, 'detect contradictory policy outcomes')

def control_35(ctx: ControlContext) -> ControlResult:
    """apply deterministic policy precedence."""
    if ctx.attributes.get("precedence_violation",False): return evaluate_control(35, 'Policy Precedence', ctx, True, 'Policy Precedence'+" failed")
    return evaluate_control(35, 'Policy Precedence', ctx, False, 'apply deterministic policy precedence')

def control_36(ctx: ControlContext) -> ControlResult:
    """attach mandatory obligations to allowed decisions."""
    if ctx.attributes.get("required_obligation_missing",False): return evaluate_control(36, 'Authorization Obligations', ctx, True, 'Authorization Obligations'+" failed")
    return evaluate_control(36, 'Authorization Obligations', ctx, False, 'attach mandatory obligations to allowed decisions')

def control_37(ctx: ControlContext) -> ControlResult:
    """evaluate declarative conditions."""
    if ctx.attributes.get("condition_failed",False): return evaluate_control(37, 'Conditional Authorization', ctx, True, 'Conditional Authorization'+" failed")
    return evaluate_control(37, 'Conditional Authorization', ctx, False, 'evaluate declarative conditions')

def control_38(ctx: ControlContext) -> ControlResult:
    """authorize from trusted attributes."""
    if ctx.attributes.get("abac_failed",False): return evaluate_control(38, 'Attribute Based Access Control', ctx, True, 'Attribute Based Access Control'+" failed")
    return evaluate_control(38, 'Attribute Based Access Control', ctx, False, 'authorize from trusted attributes')

def control_39(ctx: ControlContext) -> ControlResult:
    """bind context fields immutably."""
    if ctx.attributes.get("context_tampered",False): return evaluate_control(39, 'Context Integrity', ctx, True, 'Context Integrity'+" failed")
    return evaluate_control(39, 'Context Integrity', ctx, False, 'bind context fields immutably')

def control_40(ctx: ControlContext) -> ControlResult:
    """reject stale authorization decisions."""
    if ctx.attributes.get("stale",False): return evaluate_control(40, 'Decision Freshness', ctx, True, 'Decision Freshness'+" failed")
    return evaluate_control(40, 'Decision Freshness', ctx, False, 'reject stale authorization decisions')

def control_41(ctx: ControlContext) -> ControlResult:
    """reject replayed authorization requests."""
    if ctx.attributes.get("replayed",False): return evaluate_control(41, 'Replay Protection', ctx, True, 'Replay Protection'+" failed")
    return evaluate_control(41, 'Replay Protection', ctx, False, 'reject replayed authorization requests')

def control_42(ctx: ControlContext) -> ControlResult:
    """return stable outcomes for duplicate requests."""
    if ctx.attributes.get("duplicate_inconsistent",False): return evaluate_control(42, 'Idempotent Authorization', ctx, True, 'Idempotent Authorization'+" failed")
    return evaluate_control(42, 'Idempotent Authorization', ctx, False, 'return stable outcomes for duplicate requests')

def control_43(ctx: ControlContext) -> ControlResult:
    """bound repeated authorization attempts."""
    if ctx.attributes.get("rate_exceeded",False): return evaluate_control(43, 'Authorization Rate Limiting', ctx, True, 'Authorization Rate Limiting'+" failed")
    return evaluate_control(43, 'Authorization Rate Limiting', ctx, False, 'bound repeated authorization attempts')

def control_44(ctx: ControlContext) -> ControlResult:
    """temporarily block abusive actors."""
    if ctx.attributes.get("abuse_locked",False): return evaluate_control(44, 'Abuse Lockout', ctx, True, 'Abuse Lockout'+" failed")
    return evaluate_control(44, 'Abuse Lockout', ctx, False, 'temporarily block abusive actors')

def control_45(ctx: ControlContext) -> ControlResult:
    """deny when anomaly threshold is exceeded."""
    if ctx.attributes.get("anomaly_high",False): return evaluate_control(45, 'Anomaly Detection Boundary', ctx, True, 'Anomaly Detection Boundary'+" failed")
    return evaluate_control(45, 'Anomaly Detection Boundary', ctx, False, 'deny when anomaly threshold is exceeded')

def control_46(ctx: ControlContext) -> ControlResult:
    """deny when contextual risk exceeds policy."""
    if ctx.risk_score>ctx.attributes.get("risk_threshold",100): return evaluate_control(46, 'Risk Threshold Enforcement', ctx, True, 'Risk Threshold Enforcement'+" failed")
    return evaluate_control(46, 'Risk Threshold Enforcement', ctx, False, 'deny when contextual risk exceeds policy')

def control_47(ctx: ControlContext) -> ControlResult:
    """select assurance requirements from risk."""
    if ctx.risk_score>=ctx.attributes.get("adaptive_high_risk",90) and ctx.assurance!="strong": return evaluate_control(47, 'Adaptive Risk Authorization', ctx, True, 'Adaptive Risk Authorization'+" failed")
    return evaluate_control(47, 'Adaptive Risk Authorization', ctx, False, 'select assurance requirements from risk')

def control_48(ctx: ControlContext) -> ControlResult:
    """raise controls for sensitive resources."""
    if ctx.attributes.get("sensitive_resource",False) and ctx.assurance!="strong": return evaluate_control(48, 'Sensitive Resource Protection', ctx, True, 'Sensitive Resource Protection'+" failed")
    return evaluate_control(48, 'Sensitive Resource Protection', ctx, False, 'raise controls for sensitive resources')

def control_49(ctx: ControlContext) -> ControlResult:
    """prevent unauthorized sensitive-field access."""
    if ctx.attributes.get("sensitive_field",False) and not ctx.attributes.get("field_allowed",False): return evaluate_control(49, 'Sensitive Field Protection', ctx, True, 'Sensitive Field Protection'+" failed")
    return evaluate_control(49, 'Sensitive Field Protection', ctx, False, 'prevent unauthorized sensitive-field access')

def control_50(ctx: ControlContext) -> ControlResult:
    """limit high-impact bulk actions."""
    if ctx.attributes.get("bulk",False) and not ctx.attributes.get("bulk_allowed",False): return evaluate_control(50, 'Bulk Operation Guard', ctx, True, 'Bulk Operation Guard'+" failed")
    return evaluate_control(50, 'Bulk Operation Guard', ctx, False, 'limit high-impact bulk actions')

def control_51(ctx: ControlContext) -> ControlResult:
    """protect data export actions."""
    if ctx.action=="export" and not ctx.attributes.get("export_allowed",False): return evaluate_control(51, 'Export Authorization', ctx, True, 'Export Authorization'+" failed")
    return evaluate_control(51, 'Export Authorization', ctx, False, 'protect data export actions')

def control_52(ctx: ControlContext) -> ControlResult:
    """protect downloadable artifacts."""
    if ctx.action=="download" and not ctx.attributes.get("download_allowed",False): return evaluate_control(52, 'Download Authorization', ctx, True, 'Download Authorization'+" failed")
    return evaluate_control(52, 'Download Authorization', ctx, False, 'protect downloadable artifacts')

def control_53(ctx: ControlContext) -> ControlResult:
    """bind API operations to declared scopes."""
    if ctx.attributes.get("api_scope_missing",False): return evaluate_control(53, 'API Scope Enforcement', ctx, True, 'API Scope Enforcement'+" failed")
    return evaluate_control(53, 'API Scope Enforcement', ctx, False, 'bind API operations to declared scopes')

def control_54(ctx: ControlContext) -> ControlResult:
    """authenticate and constrain service actors."""
    if ctx.actor_type=="service" and not ctx.attributes.get("service_authenticated",False): return evaluate_control(54, 'Service-to-Service Authorization', ctx, True, 'Service-to-Service Authorization'+" failed")
    return evaluate_control(54, 'Service-to-Service Authorization', ctx, False, 'authenticate and constrain service actors')

def control_55(ctx: ControlContext) -> ControlResult:
    """constrain system actor privileges."""
    if ctx.actor_type=="system" and ctx.action in {"approve","reject"}: return evaluate_control(55, 'System Actor Boundary', ctx, True, 'System Actor Boundary'+" failed")
    return evaluate_control(55, 'System Actor Boundary', ctx, False, 'constrain system actor privileges')

def control_56(ctx: ControlContext) -> ControlResult:
    """authorize AI capabilities from a registry."""
    if ctx.actor_type=="ai" and not ctx.attributes.get("agent_capability_allowed",False): return evaluate_control(56, 'Agent Capability Registry', ctx, True, 'Agent Capability Registry'+" failed")
    return evaluate_control(56, 'Agent Capability Registry', ctx, False, 'authorize AI capabilities from a registry')

def control_57(ctx: ControlContext) -> ControlResult:
    """restrict AI tool invocation to approved capabilities."""
    if ctx.actor_type=="ai" and ctx.attributes.get("tool_unapproved",False): return evaluate_control(57, 'Agent Tool Boundary', ctx, True, 'Agent Tool Boundary'+" failed")
    return evaluate_control(57, 'Agent Tool Boundary', ctx, False, 'restrict AI tool invocation to approved capabilities')

def control_58(ctx: ControlContext) -> ControlResult:
    """prevent AI delegation of human-only actions."""
    if ctx.actor_type=="ai" and ctx.attributes.get("delegates_human_action",False): return evaluate_control(58, 'Agent Delegation Boundary', ctx, True, 'Agent Delegation Boundary'+" failed")
    return evaluate_control(58, 'Agent Delegation Boundary', ctx, False, 'prevent AI delegation of human-only actions')

def control_59(ctx: ControlContext) -> ControlResult:
    """require explicit human confirmation for designated actions."""
    if ctx.action in SENSITIVE and ctx.attributes.get("human_confirmation_required",False) and not ctx.attributes.get("human_confirmed",False): return evaluate_control(59, 'Human-in-the-Loop Gate', ctx, True, 'Human-in-the-Loop Gate'+" failed")
    return evaluate_control(59, 'Human-in-the-Loop Gate', ctx, False, 'require explicit human confirmation for designated actions')

def control_60(ctx: ControlContext) -> ControlResult:
    """require evidence references for sensitive approval."""
    if ctx.action in {"approve","reject"} and not ctx.attributes.get("evidence_refs"): return evaluate_control(60, 'Approval Evidence Requirement', ctx, True, 'Approval Evidence Requirement'+" failed")
    return evaluate_control(60, 'Approval Evidence Requirement', ctx, False, 'require evidence references for sensitive approval')

def control_61(ctx: ControlContext) -> ControlResult:
    """expire pending approvals."""
    if ctx.attributes.get("approval_expired",False): return evaluate_control(61, 'Approval Expiration', ctx, True, 'Approval Expiration'+" failed")
    return evaluate_control(61, 'Approval Expiration', ctx, False, 'expire pending approvals')

def control_62(ctx: ControlContext) -> ControlResult:
    """invalidate approvals after revocation."""
    if ctx.attributes.get("approval_revoked",False): return evaluate_control(62, 'Approval Revocation', ctx, True, 'Approval Revocation'+" failed")
    return evaluate_control(62, 'Approval Revocation', ctx, False, 'invalidate approvals after revocation')

def control_63(ctx: ControlContext) -> ControlResult:
    """preserve ordered approval chain."""
    if ctx.attributes.get("approval_chain_invalid",False): return evaluate_control(63, 'Approval Chain Integrity', ctx, True, 'Approval Chain Integrity'+" failed")
    return evaluate_control(63, 'Approval Chain Integrity', ctx, False, 'preserve ordered approval chain')

def control_64(ctx: ControlContext) -> ControlResult:
    """prevent reuse of approval decisions."""
    if ctx.attributes.get("approval_replayed",False): return evaluate_control(64, 'Approval Replay Protection', ctx, True, 'Approval Replay Protection'+" failed")
    return evaluate_control(64, 'Approval Replay Protection', ctx, False, 'prevent reuse of approval decisions')

def control_65(ctx: ControlContext) -> ControlResult:
    """support non-mutating authorization simulation."""
    if ctx.attributes.get("simulation_mutated",False): return evaluate_control(65, 'Policy Simulation', ctx, True, 'Policy Simulation'+" failed")
    return evaluate_control(65, 'Policy Simulation', ctx, False, 'support non-mutating authorization simulation')

def control_66(ctx: ControlContext) -> ControlResult:
    """produce deterministic reasons for outcomes."""
    if ctx.attributes.get("explainability_missing",False): return evaluate_control(66, 'Policy Explainability', ctx, True, 'Policy Explainability'+" failed")
    return evaluate_control(66, 'Policy Explainability', ctx, False, 'produce deterministic reasons for outcomes')

def control_67(ctx: ControlContext) -> ControlResult:
    """preserve ordered immutable trace."""
    if ctx.attributes.get("trace_tampered",False): return evaluate_control(67, 'Authorization Trace Integrity', ctx, True, 'Authorization Trace Integrity'+" failed")
    return evaluate_control(67, 'Authorization Trace Integrity', ctx, False, 'preserve ordered immutable trace')

def control_68(ctx: ControlContext) -> ControlResult:
    """require correlation identifiers for decisions."""
    if ctx.correlation_id is None: return evaluate_control(68, 'Audit Correlation', ctx, True, 'Audit Correlation'+" failed")
    return evaluate_control(68, 'Audit Correlation', ctx, False, 'require correlation identifiers for decisions')

def control_69(ctx: ControlContext) -> ControlResult:
    """attribute decisions to authenticated actors."""
    if not ctx.authenticated: return evaluate_control(69, 'Audit Actor Attribution', ctx, True, 'Audit Actor Attribution'+" failed")
    return evaluate_control(69, 'Audit Actor Attribution', ctx, False, 'attribute decisions to authenticated actors')

def control_70(ctx: ControlContext) -> ControlResult:
    """prevent mutation of emitted audit records."""
    if ctx.attributes.get("audit_tampered",False): return evaluate_control(70, 'Audit Tamper Boundary', ctx, True, 'Audit Tamper Boundary'+" failed")
    return evaluate_control(70, 'Audit Tamper Boundary', ctx, False, 'prevent mutation of emitted audit records')

def control_71(ctx: ControlContext) -> ControlResult:
    """classify authorization records for retention."""
    if ctx.attributes.get("retention_class_missing",False): return evaluate_control(71, 'Retention Policy Boundary', ctx, True, 'Retention Policy Boundary'+" failed")
    return evaluate_control(71, 'Retention Policy Boundary', ctx, False, 'classify authorization records for retention')

def control_72(ctx: ControlContext) -> ControlResult:
    """avoid unnecessary authorization context data."""
    if ctx.attributes.get("excess_context",False): return evaluate_control(72, 'Privacy Minimization', ctx, True, 'Privacy Minimization'+" failed")
    return evaluate_control(72, 'Privacy Minimization', ctx, False, 'avoid unnecessary authorization context data')

def control_73(ctx: ControlContext) -> ControlResult:
    """reject secret material in authorization context."""
    if ctx.attributes.get("secret_present",False): return evaluate_control(73, 'Secret Boundary Enforcement', ctx, True, 'Secret Boundary Enforcement'+" failed")
    return evaluate_control(73, 'Secret Boundary Enforcement', ctx, False, 'reject secret material in authorization context')

def control_74(ctx: ControlContext) -> ControlResult:
    """normalize identifiers before comparison."""
    if ctx.attributes.get("noncanonical_identifier",False): return evaluate_control(74, 'Input Canonicalization', ctx, True, 'Input Canonicalization'+" failed")
    return evaluate_control(74, 'Input Canonicalization', ctx, False, 'normalize identifiers before comparison')

def control_75(ctx: ControlContext) -> ControlResult:
    """avoid ambiguous policy identifiers."""
    if ctx.attributes.get("confusable_identifier",False): return evaluate_control(75, 'Unicode/Confusable Safety', ctx, True, 'Unicode/Confusable Safety'+" failed")
    return evaluate_control(75, 'Unicode/Confusable Safety', ctx, False, 'avoid ambiguous policy identifiers')

def control_76(ctx: ControlContext) -> ControlResult:
    """validate stable policy identifiers."""
    if ctx.attributes.get("invalid_policy_identifier",False): return evaluate_control(76, 'Policy Identifier Integrity', ctx, True, 'Policy Identifier Integrity'+" failed")
    return evaluate_control(76, 'Policy Identifier Integrity', ctx, False, 'validate stable policy identifiers')

def control_77(ctx: ControlContext) -> ControlResult:
    """reject unsafe authorization configuration."""
    if ctx.attributes.get("unsafe_configuration",False): return evaluate_control(77, 'Configuration Integrity', ctx, True, 'Configuration Integrity'+" failed")
    return evaluate_control(77, 'Configuration Integrity', ctx, False, 'reject unsafe authorization configuration')

def control_78(ctx: ControlContext) -> ControlResult:
    """prove unknown requests are denied."""
    if ctx.attributes.get("unknown_request",False): return evaluate_control(78, 'Default Deny Verification', ctx, True, 'Default Deny Verification'+" failed")
    return evaluate_control(78, 'Default Deny Verification', ctx, False, 'prove unknown requests are denied')

def control_79(ctx: ControlContext) -> ControlResult:
    """prove evaluator failures deny access."""
    if ctx.attributes.get("evaluator_failed",False): return evaluate_control(79, 'Fail Closed Verification', ctx, True, 'Fail Closed Verification'+" failed")
    return evaluate_control(79, 'Fail Closed Verification', ctx, False, 'prove evaluator failures deny access')

def control_80(ctx: ControlContext) -> ControlResult:
    """keep safety controls active on partial failure."""
    if ctx.attributes.get("partial_failure",False) and not ctx.attributes.get("safety_active",False): return evaluate_control(80, 'Fail Safe Boundary', ctx, True, 'Fail Safe Boundary'+" failed")
    return evaluate_control(80, 'Fail Safe Boundary', ctx, False, 'keep safety controls active on partial failure')

def control_81(ctx: ControlContext) -> ControlResult:
    """deny when required authorization dependencies are unhealthy."""
    if ctx.attributes.get("dependency_unhealthy",False): return evaluate_control(81, 'Dependency Health Gate', ctx, True, 'Dependency Health Gate'+" failed")
    return evaluate_control(81, 'Dependency Health Gate', ctx, False, 'deny when required authorization dependencies are unhealthy')

def control_82(ctx: ControlContext) -> ControlResult:
    """prevent stale or cross-tenant authorization cache reuse."""
    if ctx.attributes.get("cache_cross_tenant",False) or ctx.attributes.get("cache_stale",False): return evaluate_control(82, 'Cache Safety', ctx, True, 'Cache Safety'+" failed")
    return evaluate_control(82, 'Cache Safety', ctx, False, 'prevent stale or cross-tenant authorization cache reuse')

def control_83(ctx: ControlContext) -> ControlResult:
    """invalidate authorization outcomes on policy changes."""
    if ctx.attributes.get("cache_not_invalidated",False): return evaluate_control(83, 'Cache Invalidation', ctx, True, 'Cache Invalidation'+" failed")
    return evaluate_control(83, 'Cache Invalidation', ctx, False, 'invalidate authorization outcomes on policy changes')

def control_84(ctx: ControlContext) -> ControlResult:
    """protect authorization state under concurrent requests."""
    if ctx.attributes.get("concurrency_conflict",False): return evaluate_control(84, 'Concurrency Safety', ctx, True, 'Concurrency Safety'+" failed")
    return evaluate_control(84, 'Concurrency Safety', ctx, False, 'protect authorization state under concurrent requests')

def control_85(ctx: ControlContext) -> ControlResult:
    """require consistent policy/resource snapshots."""
    if ctx.attributes.get("inconsistent_snapshot",False): return evaluate_control(85, 'Consistency Boundary', ctx, True, 'Consistency Boundary'+" failed")
    return evaluate_control(85, 'Consistency Boundary', ctx, False, 'require consistent policy/resource snapshots')

def control_86(ctx: ControlContext) -> ControlResult:
    """bind authorization to transaction identity."""
    if ctx.attributes.get("transaction_mismatch",False): return evaluate_control(86, 'Transactional Authorization', ctx, True, 'Transactional Authorization'+" failed")
    return evaluate_control(86, 'Transactional Authorization', ctx, False, 'bind authorization to transaction identity')

def control_87(ctx: ControlContext) -> ControlResult:
    """deny when required state is not converged."""
    if ctx.attributes.get("state_not_converged",False): return evaluate_control(87, 'Eventual Consistency Guard', ctx, True, 'Eventual Consistency Guard'+" failed")
    return evaluate_control(87, 'Eventual Consistency Guard', ctx, False, 'deny when required state is not converged')

def control_88(ctx: ControlContext) -> ControlResult:
    """preserve authorization semantics across versions."""
    if ctx.attributes.get("migration_semantic_break",False): return evaluate_control(88, 'Migration Compatibility', ctx, True, 'Migration Compatibility'+" failed")
    return evaluate_control(88, 'Migration Compatibility', ctx, False, 'preserve authorization semantics across versions')

def control_89(ctx: ControlContext) -> ControlResult:
    """reject incompatible legacy authorization contracts."""
    if ctx.attributes.get("legacy_incompatible",False): return evaluate_control(89, 'Backward Compatibility', ctx, True, 'Backward Compatibility'+" failed")
    return evaluate_control(89, 'Backward Compatibility', ctx, False, 'reject incompatible legacy authorization contracts')

def control_90(ctx: ControlContext) -> ControlResult:
    """negotiate supported authorization contract versions."""
    if ctx.attributes.get("unsupported_version",False): return evaluate_control(90, 'Version Negotiation', ctx, True, 'Version Negotiation'+" failed")
    return evaluate_control(90, 'Version Negotiation', ctx, False, 'negotiate supported authorization contract versions')

def control_91(ctx: ControlContext) -> ControlResult:
    """constrain staged policy rollout."""
    if ctx.attributes.get("rollout_blocked",False): return evaluate_control(91, 'Policy Rollout Guard', ctx, True, 'Policy Rollout Guard'+" failed")
    return evaluate_control(91, 'Policy Rollout Guard', ctx, False, 'constrain staged policy rollout')

def control_92(ctx: ControlContext) -> ControlResult:
    """support deterministic canary evaluation."""
    if ctx.attributes.get("canary_mismatch",False): return evaluate_control(92, 'Canary Authorization', ctx, True, 'Canary Authorization'+" failed")
    return evaluate_control(92, 'Canary Authorization', ctx, False, 'support deterministic canary evaluation')

def control_93(ctx: ControlContext) -> ControlResult:
    """allow safe policy rollback with version checks."""
    if ctx.attributes.get("rollback_version_invalid",False): return evaluate_control(93, 'Policy Rollback Guard', ctx, True, 'Policy Rollback Guard'+" failed")
    return evaluate_control(93, 'Policy Rollback Guard', ctx, False, 'allow safe policy rollback with version checks')

def control_94(ctx: ControlContext) -> ControlResult:
    """support explicit authorization lockdown."""
    if ctx.attributes.get("lockdown",False) and not ctx.attributes.get("lockdown_override",False): return evaluate_control(94, 'Incident Lockdown', ctx, True, 'Incident Lockdown'+" failed")
    return evaluate_control(94, 'Incident Lockdown', ctx, False, 'support explicit authorization lockdown')

def control_95(ctx: ControlContext) -> ControlResult:
    """constrain recovery operations."""
    if ctx.action=="recover" and not ctx.attributes.get("recovery_allowed",False): return evaluate_control(95, 'Recovery Authorization', ctx, True, 'Recovery Authorization'+" failed")
    return evaluate_control(95, 'Recovery Authorization', ctx, False, 'constrain recovery operations')

def control_96(ctx: ControlContext) -> ControlResult:
    """preserve default-deny during recovery."""
    if ctx.attributes.get("disaster_recovery",False) and not ctx.attributes.get("recovery_safe",False): return evaluate_control(96, 'Disaster Recovery Boundary', ctx, True, 'Disaster Recovery Boundary'+" failed")
    return evaluate_control(96, 'Disaster Recovery Boundary', ctx, False, 'preserve default-deny during recovery')

def control_97(ctx: ControlContext) -> ControlResult:
    """define cumulative security acceptance gate."""
    if ctx.attributes.get("regression_failed",False): return evaluate_control(97, 'Security Regression Gate', ctx, True, 'Security Regression Gate'+" failed")
    return evaluate_control(97, 'Security Regression Gate', ctx, False, 'define cumulative security acceptance gate')

def control_98(ctx: ControlContext) -> ControlResult:
    """certify policy/control inventory."""
    if ctx.attributes.get("certification_failed",False): return evaluate_control(98, 'Authorization Certification', ctx, True, 'Authorization Certification'+" failed")
    return evaluate_control(98, 'Authorization Certification', ctx, False, 'certify policy/control inventory')

def control_99(ctx: ControlContext) -> ControlResult:
    """block release unless all controls pass."""
    if ctx.attributes.get("release_gate_failed",False): return evaluate_control(99, 'Authorization Release Gate', ctx, True, 'Authorization Release Gate'+" failed")
    return evaluate_control(99, 'Authorization Release Gate', ctx, False, 'block release unless all controls pass')

def control_100(ctx: ControlContext) -> ControlResult:
    """close V104.05 authorization implementation with evidence."""
    if ctx.attributes.get("master_closure_blocked",False): return evaluate_control(100, 'Authorization Master Closure', ctx, True, 'Authorization Master Closure'+" failed")
    return evaluate_control(100, 'Authorization Master Closure', ctx, False, 'close V104.05 authorization implementation with evidence')

CONTROL_REGISTRY=(
    (11, 'Authorization Boundary & Abuse Tests', control_11),
    (12, 'Privilege Escalation Prevention', control_12),
    (13, 'Separation of Duties', control_13),
    (14, 'Least Privilege Enforcement', control_14),
    (15, 'Deny Override Protection', control_15),
    (16, 'Delegated Authorization', control_16),
    (17, 'Delegation Expiry', control_17),
    (18, 'Approval Separation', control_18),
    (19, 'Four Eyes Control', control_19),
    (20, 'Resource Hierarchy Authorization', control_20),
    (21, 'Ownership Boundary', control_21),
    (22, 'Tenant Isolation Hardening', control_22),
    (23, 'Cross Tenant Denial', control_23),
    (24, 'Temporal Authorization', control_24),
    (25, 'Context Attribute Integrity', control_25),
    (26, 'Session Assurance Enforcement', control_26),
    (27, 'Step Up Authorization', control_27),
    (28, 'Reauthentication Boundary', control_28),
    (29, 'Token Revocation Enforcement', control_29),
    (30, 'Credential State Enforcement', control_30),
    (31, 'Emergency Access Boundary', control_31),
    (32, 'Emergency Access Audit', control_32),
    (33, 'Policy Versioning', control_33),
    (34, 'Policy Conflict Detection', control_34),
    (35, 'Policy Precedence', control_35),
    (36, 'Authorization Obligations', control_36),
    (37, 'Conditional Authorization', control_37),
    (38, 'Attribute Based Access Control', control_38),
    (39, 'Context Integrity', control_39),
    (40, 'Decision Freshness', control_40),
    (41, 'Replay Protection', control_41),
    (42, 'Idempotent Authorization', control_42),
    (43, 'Authorization Rate Limiting', control_43),
    (44, 'Abuse Lockout', control_44),
    (45, 'Anomaly Detection Boundary', control_45),
    (46, 'Risk Threshold Enforcement', control_46),
    (47, 'Adaptive Risk Authorization', control_47),
    (48, 'Sensitive Resource Protection', control_48),
    (49, 'Sensitive Field Protection', control_49),
    (50, 'Bulk Operation Guard', control_50),
    (51, 'Export Authorization', control_51),
    (52, 'Download Authorization', control_52),
    (53, 'API Scope Enforcement', control_53),
    (54, 'Service-to-Service Authorization', control_54),
    (55, 'System Actor Boundary', control_55),
    (56, 'Agent Capability Registry', control_56),
    (57, 'Agent Tool Boundary', control_57),
    (58, 'Agent Delegation Boundary', control_58),
    (59, 'Human-in-the-Loop Gate', control_59),
    (60, 'Approval Evidence Requirement', control_60),
    (61, 'Approval Expiration', control_61),
    (62, 'Approval Revocation', control_62),
    (63, 'Approval Chain Integrity', control_63),
    (64, 'Approval Replay Protection', control_64),
    (65, 'Policy Simulation', control_65),
    (66, 'Policy Explainability', control_66),
    (67, 'Authorization Trace Integrity', control_67),
    (68, 'Audit Correlation', control_68),
    (69, 'Audit Actor Attribution', control_69),
    (70, 'Audit Tamper Boundary', control_70),
    (71, 'Retention Policy Boundary', control_71),
    (72, 'Privacy Minimization', control_72),
    (73, 'Secret Boundary Enforcement', control_73),
    (74, 'Input Canonicalization', control_74),
    (75, 'Unicode/Confusable Safety', control_75),
    (76, 'Policy Identifier Integrity', control_76),
    (77, 'Configuration Integrity', control_77),
    (78, 'Default Deny Verification', control_78),
    (79, 'Fail Closed Verification', control_79),
    (80, 'Fail Safe Boundary', control_80),
    (81, 'Dependency Health Gate', control_81),
    (82, 'Cache Safety', control_82),
    (83, 'Cache Invalidation', control_83),
    (84, 'Concurrency Safety', control_84),
    (85, 'Consistency Boundary', control_85),
    (86, 'Transactional Authorization', control_86),
    (87, 'Eventual Consistency Guard', control_87),
    (88, 'Migration Compatibility', control_88),
    (89, 'Backward Compatibility', control_89),
    (90, 'Version Negotiation', control_90),
    (91, 'Policy Rollout Guard', control_91),
    (92, 'Canary Authorization', control_92),
    (93, 'Policy Rollback Guard', control_93),
    (94, 'Incident Lockdown', control_94),
    (95, 'Recovery Authorization', control_95),
    (96, 'Disaster Recovery Boundary', control_96),
    (97, 'Security Regression Gate', control_97),
    (98, 'Authorization Certification', control_98),
    (99, 'Authorization Release Gate', control_99),
    (100, 'Authorization Master Closure', control_100),
)

def evaluate_all(ctx):
    results=[]
    for stage,name,fn in CONTROL_REGISTRY:
        r=fn(ctx); results.append(r)
        if not r.allowed: break
    return tuple(results)

def master_status(ctx):
    r=evaluate_all(ctx)
    return len(r)==len(CONTROL_REGISTRY) and all(x.allowed for x in r)
