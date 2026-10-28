from app.infrastructure.api_repository import ApiRecordRepository
from app.infrastructure.database import Database


def test_api_records_persist_across_repository_instances(tmp_path):
    url = f"sqlite:///{tmp_path / 'api-records.db'}"
    first = ApiRecordRepository(Database(url))
    record = {"id": "org-1", "name": "Example", "status": "active", "version": 1}
    first.add("organizations", record)

    second = ApiRecordRepository(Database(url))
    assert second.get("organizations", "org-1") == record
    assert second.list("organizations") == [record]


def test_api_record_update_is_durable(tmp_path):
    url = f"sqlite:///{tmp_path / 'api-update.db'}"
    first = ApiRecordRepository(Database(url))
    record = {"id": "decision-1", "title": "Initial", "status": "draft", "version": 1}
    first.add("decisions", record)
    updated = {**record, "status": "review", "version": 2}
    first.update("decisions", updated)

    second = ApiRecordRepository(Database(url))
    assert second.get("decisions", "decision-1") == updated


def test_api_record_rejects_unknown_resource(tmp_path):
    repository = ApiRecordRepository(Database(f"sqlite:///{tmp_path / 'unknown.db'}"))
    try:
        repository.list("users")
    except ValueError as exc:
        assert "unsupported API resource" in str(exc)
    else:
        raise AssertionError("unsupported resource must be rejected")


def test_api_records_list_for_tenant_returns_only_matching_records(tmp_path):
    repository = ApiRecordRepository(
        Database(f"sqlite:///{tmp_path / 'tenant-list.db'}")
    )
    tenant_a = {
        "id": "risk-a",
        "tenant_id": "tenant-a",
        "title": "Tenant A risk",
    }
    tenant_b = {
        "id": "risk-b",
        "tenant_id": "tenant-b",
        "title": "Tenant B risk",
    }
    repository.add("risks", tenant_a)
    repository.add("risks", tenant_b)

    assert repository.list_for_tenant("risks", "tenant-a") == [tenant_a]


def test_api_records_get_for_tenant_hides_foreign_record(tmp_path):
    repository = ApiRecordRepository(
        Database(f"sqlite:///{tmp_path / 'tenant-get.db'}")
    )
    record = {
        "id": "decision-b",
        "tenant_id": "tenant-b",
        "title": "Private decision",
    }
    repository.add("decisions", record)

    assert repository.get_for_tenant(
        "decisions", "decision-b", "tenant-a"
    ) is None


def test_api_records_update_for_tenant_rejects_foreign_record(tmp_path):
    repository = ApiRecordRepository(
        Database(f"sqlite:///{tmp_path / 'tenant-update.db'}")
    )
    original = {
        "id": "decision-b",
        "tenant_id": "tenant-b",
        "title": "Original title",
        "version": 1,
    }
    repository.add("decisions", original)
    attempted_update = {
        **original,
        "title": "Unauthorized change",
        "version": 2,
    }

    try:
        repository.update_for_tenant(
            "decisions", attempted_update, "tenant-a"
        )
    except KeyError:
        pass
    else:
        raise AssertionError("cross-tenant update must be rejected")

    assert repository.get("decisions", "decision-b") == original
