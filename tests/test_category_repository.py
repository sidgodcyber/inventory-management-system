"""Tests for :mod:`repositories.category_repository`.

Layer: tests
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import pytest

from core.database import Database
from models.common import ListQuery
from repositories.category_repository import CategoryRepository


@pytest.fixture()
def repo(db: Database) -> CategoryRepository:
    """Repository bound to the temporary database."""
    return CategoryRepository(db)


def test_create_and_get(repo: CategoryRepository) -> None:
    """A created category can be read back by id and by name."""
    new_id = repo.create("Stationery", "Pens and paper")
    category = repo.get(new_id)
    assert category is not None and category.name == "Stationery"
    assert repo.get_by_name("stationery").id == new_id
    assert category.created_at and category.product_count == 0


def test_update_changes_fields(repo: CategoryRepository) -> None:
    """Updates persist."""
    new_id = repo.create("Stationary", "")
    repo.update(new_id, "Stationery", "Fixed typo")
    assert repo.get(new_id).description == "Fixed typo"


def test_delete_removes_row(repo: CategoryRepository) -> None:
    """Deleted categories are gone."""
    new_id = repo.create("Temp", "")
    repo.delete(new_id)
    assert repo.get(new_id) is None


def test_list_search_sort_and_paginate(repo: CategoryRepository) -> None:
    """Search filters, sort orders and pages slice correctly."""
    for name in ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]:
        repo.create(name, f"{name} items")
    page = repo.find(ListQuery(sort_by="name", descending=True, page=1, page_size=2))
    assert [c.name for c in page.items] == ["Gamma", "Epsilon"]
    assert (page.total, page.pages) == (5, 3)
    assert repo.find(ListQuery(search="lph")).total == 1


def test_unknown_sort_key_falls_back_safely(repo: CategoryRepository) -> None:
    """A non-whitelisted sort key cannot inject SQL."""
    repo.create("Alpha", "")
    page = repo.find(ListQuery(sort_by="name; DROP TABLE categories"))
    assert page.total == 1


def test_page_number_is_clamped(repo: CategoryRepository) -> None:
    """Asking for a page past the end returns the last page."""
    repo.create("Only", "")
    assert repo.find(ListQuery(page=99)).page == 1
