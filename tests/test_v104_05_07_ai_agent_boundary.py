from uuid import uuid4
import pytest
from app.modules.authorization.domain import *
from app.modules.identity.domain.security_identity import SecurityIdentity, ActorContext

def ctx(action="read",authenticated=True):
 uid,auth,tenant,corr=uuid4(),uuid4(),uuid4(),uuid4(); i=SecurityIdentity(uid,auth,"standard",authenticated); a=ActorContext(uid,auth,corr,"ai",authenticated); r=Resource(ResourceType.PROJECT,uuid4(),tenant); return AuthorizationContext(i,a,tenant,Permission(ResourceType.PROJECT,Action(action)),r,corr)
@pytest.mark.parametrize("action",["read","create","update"])
def test_ai_is_limited_to_non_privileged_actions(action): assert AIAgentAuthorizationEngine().evaluate(ctx(action)).allowed
@pytest.mark.parametrize("action",["approve","reject","execute","archive","delete"])
def test_ai_cannot_cross_human_governance_boundary(action): assert not AIAgentAuthorizationEngine().evaluate(ctx(action)).allowed
def test_ai_identity_must_be_authenticated(): assert not AIAgentAuthorizationEngine().evaluate(ctx(authenticated=False)).allowed
def test_non_ai_is_not_restricted_by_ai_engine():
 c=ctx("approve"); object.__setattr__(c.actor,"actor_type","human"); assert AIAgentAuthorizationEngine().evaluate(c).allowed
