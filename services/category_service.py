"""Business rules for categories: validation, uniqueness, safe delete, audit.

Layer: services (talks to repositories; never contains SQL or widgets)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from core.constants import ACTION_CREATE, ACTION_DELETE, ACTION_UPDATE, ENTITY_CATEGORY
from core.database import Database
from core.exceptions import NotFoundError, ValidationError
from core.logger import diff_changes, log_activity
from models.category import Category
from models.common import ListQuery, Page
from repositories.category_repository import CategoryRepository
from utils.validators import Validator


class CategoryService:
    """Create, update, delete and list categories.

    Args:
        repo: Category repository.
        validator: Config-driven field validator.
        db: Database, used only to open atomic transactions.
    """

    def __init__(self, repo: CategoryRepository, validator: Validator, db: Database) -> None:
        self._repo = repo
        self._validate = validator
        self._db = db

    def find(self, query: ListQuery) -> Page[Category]:
        """Return one page of categories matching ``query``."""
        return self._repo.find(query)

    def list_all(self) -> list[Category]:
        """Return every category (for drop-downs)."""
        return self._repo.list_all()

    def get(self, category_id: int) -> Category:
        """Return a category.

        Raises:
            NotFoundError: If it does not exist.
        """
        category = self._repo.get(category_id)
        if category is None:
            raise NotFoundError(f"Category #{category_id} no longer exists.")
        return category

    def create(self, name: str, description: str = "") -> Category:
        """Validate and create a category, logging ``CREATE``.

        Raises:
            ValidationError: If the name is blank, too long or already used.
        """
        clean_name, clean_desc = self._clean(name, description)
        self._ensure_unique(clean_name)
        with self._db.transaction():
            new_id = self._repo.create(clean_name, clean_desc)
            log_activity(ACTION_CREATE, ENTITY_CATEGORY, new_id,
                         {"new": {"name": clean_name, "description": clean_desc}})
        return self.get(new_id)

    def update(self, category_id: int, name: str, description: str = "") -> Category:
        """Validate and update a category, logging old -> new values.

        Raises:
            NotFoundError: If the category does not exist.
            ValidationError: If the new name is invalid or taken.
        """
        current = self.get(category_id)
        clean_name, clean_desc = self._clean(name, description)
        self._ensure_unique(clean_name, exclude_id=category_id)
        changes = diff_changes(
            {"name": current.name, "description": current.description},
            {"name": clean_name, "description": clean_desc},
        )
        if changes:
            with self._db.transaction():
                self._repo.update(category_id, clean_name, clean_desc)
                log_activity(ACTION_UPDATE, ENTITY_CATEGORY, category_id, {"changes": changes})
        return self.get(category_id)

    def delete(self, category_id: int) -> None:
        """Delete an unused category, logging ``DELETE``.

        Raises:
            ValidationError: If any product (even soft-deleted) still uses it.
        """
        category = self.get(category_id)
        in_use = self._repo.count_products(category_id)
        if in_use:
            raise ValidationError(
                f"Category '{category.name}' is used by {in_use} product(s). "
                "Move those products to another category first."
            )
        with self._db.transaction():
            self._repo.delete(category_id)
            log_activity(ACTION_DELETE, ENTITY_CATEGORY, category_id,
                         {"old": {"name": category.name, "description": category.description}})

    def _clean(self, name: str, description: str) -> tuple[str, str]:
        """Validate the form fields."""
        return self._validate.text(name, "Category name"), self._validate.notes(
            description, "Description"
        )

    def _ensure_unique(self, name: str, exclude_id: int | None = None) -> None:
        """Refuse a name that another category already uses (case-insensitive)."""
        existing = self._repo.get_by_name(name)
        if existing and existing.id != exclude_id:
            raise ValidationError(f"A category named '{existing.name}' already exists.",
                                  "Category name")
