from uuid import uuid4
from app.modules.authorization.domain import *
from app.modules.identity.domain.security_identity import SecurityIdentity, ActorContext

def make(action="read",actor_type="human",assurance="strong"):
 uid,auth,tenant,corr=uuid4(),uuid4(),uuid4(),uuid4(); i=SecurityIdentity(uid,auth,assurance,True); a=ActorContext(uid,auth,corr,actor_type,True); r=Resource(ResourceType.PROJECT,uuid4(),tenant); return AuthorizationContext(i,a,tenant,Permission(ResourceType.PROJECT,Action(action)),r,corr)
def test_full_pipeline_orders_mandatory_action_ai_then_policy():
 c=make(); e=AuthorizationPolicyEngine(policies=(ExplicitPermissionPolicy(frozenset({"project:read"})),)).evaluate_with_trace(c); assert [x.stage for x in e.evaluations]==["mandatory-rule"]*5+["action","ai-boundary","policy"]
def test_ai_is_stopped_before_general_allow_policy():
 c=make("read","ai"); e=AuthorizationPolicyEngine(policies=(ExplicitPermissionPolicy(frozenset({"project:read"})),)).evaluate_with_trace(c); assert e.decision.allowed and e.evaluations[-2].stage=="ai-boundary"
def test_human_approval_service_is_separate_explicit_gate():
 c=make("approve"); object.__setattr__(c.resource,"resource_type",ResourceType.DECISION); object.__setattr__(c.permission,"resource",ResourceType.DECISION); assert HumanApprovalAuthorizationService().authorize(c).allowed
