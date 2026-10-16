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
