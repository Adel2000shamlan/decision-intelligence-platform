from pathlib import Path


def test_project_domain_dependency_boundary():
    root = Path(__file__).parents[1] / 'app' / 'modules' / 'project' / 'domain'
    forbidden = ('fastapi', 'sqlalchemy', 'postgres', 'redis', 'httpx', 'requests')
    for path in root.glob('*.py'):
        text = path.read_text().lower()
        assert not any(token in text for token in forbidden), path
