from fastapi.testclient import TestClient
from app.main import app
from app.shared.domain.state_machine import transition
from app.shared.domain.services import RiskScoreService
c=TestClient(app)
def test_health(): assert c.get('/api/v1/health').status_code==200
def test_state(): assert transition('decision','draft','validated')=='validated'
def test_risk(): assert RiskScoreService().calculate(.5,10)==5
def test_flow():
    p=c.post('/api/v1/projects',json={'name':'Demo'}).json(); d=c.post('/api/v1/decisions',json={'project_id':p['id'],'title':'Choose','objective':'Grow'}).json(); r=c.post('/api/v1/risks',json={'project_id':p['id'],'title':'Cost','probability':.4,'impact':10}).json(); assert r['score']==4
