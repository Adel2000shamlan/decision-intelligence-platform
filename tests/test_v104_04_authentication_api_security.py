from fastapi.testclient import TestClient
from app.main import app
from app.modules.authentication.api import users,credentials,tokens
from app.modules.identity.domain.models import User

def test_auth_api_register_login_logout():
 u=User.create('api@example.com','API User'); users.save(u)
 r=TestClient(app).post('/auth/credentials/register',json={'user_id':str(u.id),'password':'StrongPass123!'})
 assert r.status_code==200
 r=TestClient(app).post('/auth/login',json={'email':'api@example.com','password':'StrongPass123!'})
 assert r.status_code==200; data=r.json(); assert data['access_token']
 r=TestClient(app).post('/auth/logout',headers={'Authorization':'Bearer '+data['access_token']}); assert r.status_code==200

def test_api_bad_login_does_not_authenticate():
 r=TestClient(app).post('/auth/login',json={'email':'missing@example.com','password':'BadPassword123!'})
 assert r.status_code==401
