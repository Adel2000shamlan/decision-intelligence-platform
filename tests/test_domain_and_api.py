from fastapi.testclient import TestClient
from app.main import app
from app.shared.domain.state_machine import transition
from app.shared.domain.services import RiskScoreService
c=TestClient(app)
def test_health(): assert c.get('/api/v1/health').status_code==200
def test_state(): assert transition('decision','draft','validated')=='validated'
def test_risk(): assert RiskScoreService().calculate(.5,10)==5
def test_flow():
    from uuid import uuid4
    organization_id = uuid4()
    p = c.post('/api/v1/projects', json={'organization_id': str(organization_id), 'name': 'Demo'})
    assert p.status_code == 200
    project = p.json()
    assert project['organization_id'] == str(organization_id)
    r = c.post('/api/v1/risks', json={'project_id': project['id'], 'title': 'Cost', 'probability': .4, 'impact': 10}).json()
    assert r['score'] == 4
