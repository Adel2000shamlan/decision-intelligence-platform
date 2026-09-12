from uuid import uuid4
from datetime import datetime,timezone,timedelta
import pytest
from app.modules.authentication.security import *

def test_hash_verify_and_no_plaintext():
 p=PasswordSecurityPolicy(min_length=8); h=PasswordHasher(p); x=h.hash('Strong123!'); assert h.verify('Strong123!',x); assert not h.verify('wrong',x); assert 'Strong123!' not in x.encoded()
def test_policy():
 p=PasswordSecurityPolicy(min_length=12)
 for x in ['short','alllowercase1234','ALLUPPERCASE1234']:
  with pytest.raises(PasswordPolicyError): p.validate(x)
def test_registration_duplicate_and_rotation():
 uid=uuid4(); c=CredentialService(policy=PasswordSecurityPolicy(min_length=8)); c.register(uid,'Strong123!')
 with pytest.raises(CredentialError): c.register(uid,'Other123!')
 assert c.verify(uid,'Strong123!'); c.change(uid,'Strong123!','NewStrong123!'); assert c.verify(uid,'NewStrong123!'); assert not c.verify(uid,'Strong123!')
def test_compromise_and_revoke():
 uid=uuid4(); c=CredentialService(policy=PasswordSecurityPolicy(min_length=8)); c.register(uid,'Strong123!'); c.compromise(uid); assert c.repo.active(uid) is None; c.register(uid,'OtherStrong123!'); c.revoke(uid); assert c.repo.active(uid) is None
def test_reset_one_time_and_expiry():
 uid=uuid4(); c=CredentialService(policy=PasswordSecurityPolicy(min_length=8)); r=RecoveryService(c); tok=r.request(uid); r.consume(tok,'Strong123!');
 with pytest.raises(CredentialError): r.consume(tok,'Other123!')
def test_tokens_lifecycle():
 uid=uuid4(); t=TokenService(); a,r=t.issue(uid); rec=t.validate(a); assert rec.user_id==uid; t.revoke_session(rec.session_id)
 with pytest.raises(TokenError): t.validate(a)
def test_rbac_tenant_isolation():
 uid=uuid4(); t1=uuid4(); t2=uuid4(); rb=RBAC(); rb.define('admin',{'x'}); rb.assign(uid,'admin',t1); rb.require(uid,t1,'x')
 with pytest.raises(AuthorizationError): rb.require(uid,t2,'x')
def test_auth_login():
 from app.modules.identity.domain.models import User
 from app.modules.identity.in_memory import InMemoryUserRepository
 repo=InMemoryUserRepository(); u=User.create('a@example.com','A'); repo.save(u); c=CredentialService(policy=PasswordSecurityPolicy(min_length=8)); c.register(u.id,'Strong123!'); a=AuthenticationService(repo,c,TokenService(),RBAC()); s,at,rt=a.login('a@example.com','Strong123!'); assert s.user_id==u.id; assert at and rt
def test_password_reset_rotates_existing():
 uid=uuid4(); c=CredentialService(policy=PasswordSecurityPolicy(min_length=8)); c.register(uid,'Strong123!'); r=PasswordResetService(c); tok=r.request(uid); r.consume(tok,'NewStrong123!'); assert c.verify(uid,'NewStrong123!')
def test_password_reuse_blocked():
 uid=uuid4(); c=CredentialService(policy=PasswordSecurityPolicy(min_length=8)); c.register(uid,'Strong123!')
 with pytest.raises(PasswordPolicyError): c.change(uid,'Strong123!','Strong123!')
def test_refresh_rotates_refresh_token():
 uid=uuid4(); t=TokenService(); a,r=t.issue(uid); new=t.refresh(r); assert t.validate(new).user_id==uid
