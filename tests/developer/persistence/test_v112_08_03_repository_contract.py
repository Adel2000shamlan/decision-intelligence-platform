from uuid import uuid4

import pytest

from app.modules.developer.persistence.repository import DeveloperRepository


def test_repository_contract_is_abstract():
    with pytest.raises(TypeError):
        DeveloperRepository()


def test_repository_contract_defines_required_operations():
    expected = {
        "save_application",
        "get_application",
        "list_applications",
        "delete_application",
        "save_credential",
        "get_credential",
        "get_credential_by_client_id",
        "list_credentials",
        "delete_credential",
        "save_listing",
        "get_listing",
        "list_listings",
        "delete_listing",
    }

    assert expected.issubset(
        set(DeveloperRepository.__abstractmethods__)
    )


def test_repository_contract_methods_are_abstract():
    for method_name in (
        "save_application",
        "get_application",
        "list_applications",
        "delete_application",
        "save_credential",
        "get_credential",
        "get_credential_by_client_id",
        "list_credentials",
        "delete_credential",
        "save_listing",
        "get_listing",
        "list_listings",
        "delete_listing",
    ):
        method = getattr(DeveloperRepository, method_name)
        assert getattr(method, "__isabstractmethod__", False) is True


def test_repository_contract_exposes_client_id_lookup():
    assert hasattr(DeveloperRepository, "get_credential_by_client_id")
