"""Business rules for suppliers: contact validation, safe delete, audit.

Layer: services
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.constants import ACTION_CREATE, ACTION_DELETE, ACTION_UPDATE, ENTITY_SUPPLIER
from core.database import Database
from core.exceptions import NotFoundError, ValidationError
from core.logger import diff_changes, log_activity
from models.common import ListQuery, Page
from models.supplier import Supplier
from repositories.supplier_repository import SupplierRepository
from utils.validators import Validator

# Fields compared when writing UPDATE audit entries.
_AUDIT_FIELDS: tuple[str, ...] = ("name", "contact_person", "phone", "email", "address")


class SupplierService:
    """Create, update, delete and list suppliers.

    Args:
        repo: Supplier repository.
        validator: Config-driven field validator.
        db: Database, used only to open atomic transactions.
    """

    def __init__(self, repo: SupplierRepository, validator: Validator, db: Database) -> None:
        self._repo = repo
        self._validate = validator
        self._db = db

    def find(self, query: ListQuery) -> Page[Supplier]:
        """Return one page of suppliers matching ``query``."""
        return self._repo.find(query)

    def list_all(self) -> list[Supplier]:
        """Return every supplier (for drop-downs)."""
        return self._repo.list_all()

    def get(self, supplier_id: int) -> Supplier:
        """Return a supplier.

        Raises:
            NotFoundError: If it does not exist.
        """
        supplier = self._repo.get(supplier_id)
        if supplier is None:
            raise NotFoundError(f"Supplier #{supplier_id} no longer exists.")
        return supplier

    def create(self, data: Mapping[str, Any]) -> Supplier:
        """Validate form data and create a supplier, logging ``CREATE``.

        Args:
            data: ``name``, ``contact_person``, ``phone``, ``email``, ``address``.

        Raises:
            ValidationError: If any field is invalid.
        """
        supplier = self._parse(data)
        with self._db.transaction():
            new_id = self._repo.create(supplier)
            log_activity(ACTION_CREATE, ENTITY_SUPPLIER, new_id, {"new": _audit(supplier)})
        return self.get(new_id)

    def update(self, supplier_id: int, data: Mapping[str, Any]) -> Supplier:
        """Validate and update a supplier, logging old -> new values.

        Raises:
            NotFoundError: If the supplier does not exist.
            ValidationError: If any field is invalid.
        """
        current = self.get(supplier_id)
        supplier = self._parse(data)
        supplier.id = supplier_id
        changes = diff_changes(_audit(current), _audit(supplier))
        if changes:
            with self._db.transaction():
                self._repo.update(supplier)
                log_activity(ACTION_UPDATE, ENTITY_SUPPLIER, supplier_id, {"changes": changes})
        return self.get(supplier_id)

    def delete(self, supplier_id: int) -> None:
        """Delete a supplier no product references, logging ``DELETE``.

        Raises:
            ValidationError: If products still reference the supplier.
        """
        supplier = self.get(supplier_id)
        in_use = self._repo.count_products(supplier_id)
        if in_use:
            raise ValidationError(
                f"Supplier '{supplier.name}' supplies {in_use} product(s). "
                "Assign those products to another supplier first."
            )
        with self._db.transaction():
            self._repo.delete(supplier_id)
            log_activity(ACTION_DELETE, ENTITY_SUPPLIER, supplier_id, {"old": _audit(supplier)})

    def _parse(self, data: Mapping[str, Any]) -> Supplier:
        """Turn raw form data into a validated :class:`Supplier`."""
        return Supplier(
            name=self._validate.text(data.get("name"), "Supplier name"),
            contact_person=self._validate.text(data.get("contact_person"), "Contact person",
                                               required=False),
            phone=self._validate.phone(data.get("phone")),
            email=self._validate.email(data.get("email")),
            address=self._validate.notes(data.get("address"), "Address"),
        )


def _audit(supplier: Supplier) -> dict[str, Any]:
    """The supplier fields recorded in the audit trail."""
    return {name: getattr(supplier, name) for name in _AUDIT_FIELDS}
