"""Tests for :mod:`repositories.supplier_repository`.

Layer: tests
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import pytest

from core.database import Database
from models.common import ListQuery
from models.supplier import Supplier
from repositories.supplier_repository import SupplierRepository


@pytest.fixture()
def repo(db: Database) -> SupplierRepository:
    """Repository bound to the temporary database."""
    return SupplierRepository(db)


def _supplier(name: str = "Sharma Traders", **extra: str) -> Supplier:
    """Build an unsaved supplier."""
    return Supplier(name=name, contact_person="R. Sharma", phone="9876543210",
                    email="sales@sharma.in", address="Haldwani", **extra)


def test_create_get_update_delete(repo: SupplierRepository) -> None:
    """Full CRUD round-trip."""
    new_id = repo.create(_supplier())
    supplier = repo.get(new_id)
    assert supplier.email == "sales@sharma.in"
    supplier.phone = "+91 98765 00000"
    repo.update(supplier)
    assert repo.get(new_id).phone == "+91 98765 00000"
    repo.delete(new_id)
    assert repo.get(new_id) is None


def test_find_searches_contact_fields(repo: SupplierRepository) -> None:
    """Search matches email and contact person, not just name."""
    repo.create(_supplier("Alpha"))
    repo.create(Supplier(name="Beta", email="hello@beta.com"))
    assert repo.find(ListQuery(search="beta.com")).total == 1
    assert repo.find(ListQuery(search="Sharma")).total == 1


def test_list_all_ordered(repo: SupplierRepository) -> None:
    """Drop-down list is alphabetical."""
    repo.create(_supplier("Zeta"))
    repo.create(_supplier("Alpha"))
    assert [s.name for s in repo.list_all()] == ["Alpha", "Zeta"]
    assert repo.count_products(repo.list_all()[0].id) == 0
