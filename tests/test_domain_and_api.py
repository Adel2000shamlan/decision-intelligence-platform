from fastapi.testclient import TestClient
from app.main import app
from app.shared.domain.state_machine import transition
c=TestClient(app)
def test_health(): assert c.get('/api/v1/health').status_code==200
def test_state(): assert transition('decision','draft','validated')=='validated'
def test_flow():
    from uuid import uuid4

    organization_id = uuid4()
    p = c.post(
        '/api/v1/projects',
        json={'organization_id': str(organization_id), 'name': 'Demo'},
    )
    assert p.status_code == 200

    project = p.json()
    assert project['organization_id'] == str(organization_id)

    r = c.post(
        '/api/v1/official/risks',
        json={
            'project_id': project['id'],
            'title': 'Cost',
        },
    )
    assert r.status_code == 200
    risk = r.json()
    assert risk['status'] == 'draft'
    assert risk['version'] == 1

    risk_id = risk['id']

    r = c.post(
        f'/api/v1/official/risks/{risk_id}/identify',
        json={'expected_version': 1},
    )
    assert r.status_code == 200

    r = c.post(
        f'/api/v1/official/risks/{risk_id}/assess',
        json={
            'probability': 2,
            'impact': 2,
            'expected_version': 2,
        },
    )
    assert r.status_code == 200
    assert r.json()['score'] == 4
