from uuid import uuid4
import pytest
from app.modules.authorization.domain import *
from app.modules.identity.domain.security_identity import SecurityIdentity, ActorContext

def base(action="read",actor_type="human",assurance="strong",authenticated=True):
 uid,auth,tenant,corr=uuid4(),uuid4(),uuid4(),uuid4(); i=SecurityIdentity(uid,auth,assurance,authenticated); a=ActorContext(uid,auth,corr,actor_type,authenticated); r=Resource(ResourceType.PROJECT,uuid4(),tenant); return AuthorizationContext(i,a,tenant,Permission(ResourceType.PROJECT,Action(action)),r,corr)
def test_default_deny_remains_fail_closed(): assert not AuthorizationPolicyEngine().evaluate(base()).allowed
def test_ai_privileged_attempt_cannot_be_overridden_by_allow_policy():
 c=base("execute","ai"); d=AuthorizationPolicyEngine(policies=(ExplicitPermissionPolicy(frozenset({"project:execute"})),)).evaluate(c); assert not d.allowed
def test_sensitive_action_standard_assurance_is_denied_before_policy():
 c=base("delete","human","standard"); d=AuthorizationPolicyEngine(policies=(ExplicitPermissionPolicy(frozenset({"project:delete"})),)).evaluate(c); assert not d.allowed
def test_system_approval_denied(): assert not AuthorizationPolicyEngine(policies=(ExplicitPermissionPolicy(frozenset({"project:approve"})),)).evaluate(base("approve","system")).allowed
def test_tenant_mismatch_cannot_construct_context():
 uid,auth,t1,t2,corr=uuid4(),uuid4(),uuid4(),uuid4(),uuid4(); i=SecurityIdentity(uid,auth); a=ActorContext(uid,auth,corr); r=Resource(ResourceType.PROJECT,uuid4(),t2)
 with pytest.raises(InvalidAuthorizationContext): AuthorizationContext(i,a,t1,Permission(ResourceType.PROJECT,Action.READ),r,corr)
def test_malformed_policy_fails_closed():
 class Bad:
  policy_id="bad"
  def evaluate(self,c): return "allow"
 c=base(); d=AuthorizationPolicyEngine(policies=(Bad(),)).evaluate(c); assert not d.allowed
def test_trace_is_immutable():
 c=base(); e=AuthorizationPolicyEngine().evaluate_with_trace(c); assert isinstance(e.evaluations,tuple)
