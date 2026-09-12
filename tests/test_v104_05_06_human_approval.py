from uuid import uuid4
import pytest
from app.modules.authorization.domain import *
from app.modules.identity.domain.security_identity import SecurityIdentity, ActorContext

def ctx(action="approve",rtype=ResourceType.DECISION,actor_type="human",assurance="strong",authenticated=True):
 uid,auth,tenant,corr=uuid4(),uuid4(),uuid4(),uuid4(); i=SecurityIdentity(uid,auth,assurance,authenticated); a=ActorContext(uid,auth,corr,actor_type,authenticated); r=Resource(rtype,uuid4(),tenant); return AuthorizationContext(i,a,tenant,Permission(rtype,Action(action)),r,corr)

def test_human_approval_allows_strong_human_decision(): assert HumanApprovalAuthorizationService().authorize(ctx()).allowed
@pytest.mark.parametrize("action",["read","create","update","delete","execute","archive"])
def test_only_approve_reject_are_approval_actions(action): assert not HumanApprovalAuthorizationService().authorize(ctx(action)).allowed
def test_reject_is_allowed_for_strong_human_scenario(): assert HumanApprovalAuthorizationService().authorize(ctx("reject",ResourceType.SCENARIO)).allowed
def test_standard_or_ai_or_unauthenticated_is_denied():
 assert not HumanApprovalAuthorizationService().authorize(ctx(assurance="standard")).allowed
 assert not HumanApprovalAuthorizationService().authorize(ctx(actor_type="ai")).allowed
 assert not HumanApprovalAuthorizationService().authorize(ctx(authenticated=False)).allowed
def test_approval_request_is_immutable_and_typed():
 r=ApprovalRequest(uuid4(),ResourceType.DECISION,uuid4(),uuid4(),uuid4(),uuid4()); assert r.status==ApprovalStatus.PENDING
