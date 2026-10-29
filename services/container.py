"""Composition root: builds repositories and services and wires them together.

This is the single place that knows how the layers are assembled. ``main.py``
calls :func:`build_services` once, and the UI receives the resulting
:class:`AppServices`, so views depend only on services, never on
repositories or the database.

It also performs the dependency inversion for core: the activity-log
repository is installed as the sink behind ``core.logger.log_activity``, and
the settings repository is injected into ``SettingsManager``.

Layer: services (composition root)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from dataclasses import dataclass

from config.config_loader import AppConfig
from core.database import Database
from core.logger import configure_activity_logger
from core.settings_manager import SettingsManager
from repositories.activity_log_repository import ActivityLogRepository
from repositories.category_repository import CategoryRepository
from repositories.settings_repository import SettingsRepository
from repositories.supplier_repository import SupplierRepository
from services.category_service import CategoryService
from services.supplier_service import SupplierService
from utils.validators import Validator


@dataclass
class AppServices:
    """Every service the UI may call.

    Attributes:
        config: Validated application configuration.
        db: Open database (exposed for shutdown only).
        settings_manager: Typed runtime settings.
        categories: Category service.
        suppliers: Supplier service.
    """

    config: AppConfig
    db: Database
    settings_manager: SettingsManager
    categories: CategoryService
    suppliers: SupplierService


def build_services(config: AppConfig, db: Database) -> AppServices:
    """Assemble the application from an initialised database.

    Args:
        config: Validated configuration.
        db: Database whose schema is already initialised.

    Returns:
        The wired :class:`AppServices` container.
    """
    validator = Validator(config)
    manager = SettingsManager(SettingsRepository(db), config)
    manager.seed_defaults()
    configure_activity_logger(ActivityLogRepository(db), lambda: manager.get("operator_name"))
    return AppServices(
        config=config,
        db=db,
        settings_manager=manager,
        categories=CategoryService(CategoryRepository(db), validator, db),
        suppliers=SupplierService(SupplierRepository(db), validator, db),
    )
