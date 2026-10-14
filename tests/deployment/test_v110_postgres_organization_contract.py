from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_postgres_organization_repository_exists():
    path = ROOT / "app/modules/organization/persistence/postgres.py"
    text = path.read_text(encoding="utf-8")

    assert "class PostgreSQLOrganizationRepository" in text
    assert "import psycopg" in text
    assert "CREATE TABLE IF NOT EXISTS organizations" in text
    assert "ON CONFLICT(id) DO UPDATE" in text
    assert "tenant_id" in text
    assert "get_by_id" in text
    assert "get_by_slug" in text
    assert "exists_by_slug" in text
    assert "def list(self, tenant_id=None)" in text


def test_postgres_repository_does_not_use_sqlite():
    path = ROOT / "app/modules/organization/persistence/postgres.py"
    text = path.read_text(encoding="utf-8")

    assert "sqlite3" not in text
    assert "sqlite://" not in text


def test_postgres_repository_uses_parameterized_queries():
    path = ROOT / "app/modules/organization/persistence/postgres.py"
    text = path.read_text(encoding="utf-8")

    assert "%s" in text
    assert "SELECT * FROM organizations WHERE id=%s" in text
    assert "SELECT * FROM organizations WHERE slug=%s" in text
