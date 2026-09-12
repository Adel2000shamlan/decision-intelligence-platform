from uuid import uuid4
import pytest
from app.modules.authorization.domain import *
from app.modules.identity.domain.security_identity import SecurityIdentity, ActorContext

def ctx(action="read"):
 uid,auth,tenant,corr=uuid4(),uuid4(),uuid4(),uuid4(); i=SecurityIdentity(uid,auth,"strong",True); a=ActorContext(uid,auth,corr,"human",True); r=Resource(ResourceType.PROJECT,uuid4(),tenant); return AuthorizationContext(i,a,tenant,Permission(ResourceType.PROJECT,Action(action)),r,corr)
def test_service_facade_delegates_policy_engine():
 s=build_authorization_services((ExplicitPermissionPolicy(frozenset({"project:read"})),)); assert s.authorize(ctx()).allowed
def test_service_require_denies_by_default():
 s=build_authorization_services();
 with pytest.raises(PermissionError): s.require(ctx())
def test_service_exposes_human_approval_and_ai_boundaries():
 s=build_authorization_services(); assert s.authorize_human_approval(ctx("read")).allowed is False
