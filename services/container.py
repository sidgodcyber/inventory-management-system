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
from repositories.product_repository import ProductRepository
from repositories.settings_repository import SettingsRepository
from repositories.stock_transaction_repository import StockTransactionRepository
from repositories.supplier_repository import SupplierRepository
from services.activity_service import ActivityService
from services.category_service import CategoryService
from services.product_service import ProductRepos, ProductService
from services.report_service import ReportService
from services.settings_service import SettingsService
from services.stock_service import StockService
from services.supplier_service import SupplierService
from services.system_service import SystemService
from utils.validators import Validator


@dataclass
class AppServices:
    """Every service the UI may call.

    Attributes:
        config: Validated application configuration.
        db: Open database (exposed for shutdown only).
        settings: System Settings service.
        categories: Category service.
        suppliers: Supplier service.
        products: Product service.
        stock: Stock movement service.
        reports: Turnover and dashboard analytics.
        activity: Activity log, error and login recording.
        system: About / architecture information.
    """

    config: AppConfig
    db: Database
    settings: SettingsService
    categories: CategoryService
    suppliers: SupplierService
    products: ProductService
    stock: StockService
    reports: ReportService
    activity: ActivityService
    system: SystemService


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
    activity_repo = ActivityLogRepository(db)
    configure_activity_logger(activity_repo, lambda: manager.get("operator_name"))
    repos = ProductRepos(ProductRepository(db), CategoryRepository(db), SupplierRepository(db))
    transactions = StockTransactionRepository(db)
    stock = StockService(repos.products, transactions, validator, manager, db, config)
    return AppServices(
        config=config,
        db=db,
        settings=SettingsService(manager, validator, db, config),
        categories=CategoryService(repos.categories, validator, db),
        suppliers=SupplierService(repos.suppliers, validator, db),
        products=ProductService(repos, stock, validator, manager, db, config),
        stock=stock,
        reports=ReportService(repos.products, transactions, config),
        activity=ActivityService(activity_repo, manager, db, config),
        system=SystemService(config, db),
    )
