"""Tests for the category and supplier services (validation + audit trail).

Layer: tests
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import pytest

from core.exceptions import NotFoundError, ValidationError
from services.container import AppServices


def test_create_category_logs_create(services: AppServices, audit) -> None:
    """Creating a category writes a CREATE entry with the new values."""
    category = services.categories.create("  Stationery ", "Pens")
    entry = audit("CREATE")[0]
    assert category.name == "Stationery"
    assert entry.entity == "Category" and entry.entity_id == str(category.id)
    assert entry.details["new"]["name"] == "Stationery" and entry.user == "Admin"


def test_duplicate_category_name_rejected(services: AppServices) -> None:
    """Names are unique regardless of case."""
    services.categories.create("Stationery")
    with pytest.raises(ValidationError, match="already exists"):
        services.categories.create("STATIONERY")


def test_update_category_logs_old_and_new(services: AppServices, audit) -> None:
    """UPDATE entries contain only changed fields with old -> new."""
    category = services.categories.create("Stationary")
    services.categories.update(category.id, "Stationery", "")
    changes = audit("UPDATE")[0].details["changes"]
    assert changes == {"name": {"old": "Stationary", "new": "Stationery"}}


def test_update_without_changes_logs_nothing(services: AppServices, audit) -> None:
    """Saving an unchanged form does not pollute the audit trail."""
    category = services.categories.create("Tools", "Hand tools")
    services.categories.update(category.id, "Tools", "Hand tools")
    assert audit("UPDATE") == []


def test_delete_category(services: AppServices, audit) -> None:
    """Deleting logs the old values; the record is gone afterwards."""
    category = services.categories.create("Temp")
    services.categories.delete(category.id)
    assert audit("DELETE")[0].details["old"]["name"] == "Temp"
    with pytest.raises(NotFoundError):
        services.categories.get(category.id)


def test_blank_category_name_rejected(services: AppServices, audit) -> None:
    """Validation happens before anything is written."""
    with pytest.raises(ValidationError, match="required"):
        services.categories.create("   ")
    assert audit() == []


def test_supplier_crud_with_validation(services: AppServices, audit) -> None:
    """Supplier contact fields are validated and changes are audited."""
    supplier = services.suppliers.create(
        {"name": "Sharma Traders", "phone": "+91 98765 43210", "email": "sales@sharma.in"}
    )
    services.suppliers.update(supplier.id, {**supplier.to_dict(), "phone": "0120-555-0101"})
    assert services.suppliers.get(supplier.id).phone == "0120-555-0101"
    assert audit("UPDATE")[0].details["changes"]["phone"]["new"] == "0120-555-0101"
    services.suppliers.delete(supplier.id)
    assert len(audit("DELETE")) == 1


@pytest.mark.parametrize(
    ("field", "value"), [("email", "nope"), ("phone", "12"), ("name", "")]
)
def test_supplier_invalid_fields(services: AppServices, field: str, value: str) -> None:
    """Bad email, phone or missing name are refused with a friendly message."""
    data = {"name": "Acme", field: value}
    with pytest.raises(ValidationError):
        services.suppliers.create(data)
