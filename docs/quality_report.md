# Quality report: maintainability evidence (Q11)

Generated 2026-10-30 00:50 by `scripts/quality_report.py` (radon CC + MI, docstring coverage). **Do not edit by hand.**

## Summary

| Objective | Measure | Target | Result | Verdict |
|-----------|---------|--------|--------|---------|
| QO6 | Average cyclomatic complexity | ≤ 5 (grade A) | 2.09 (grade A) | ✅ PASS |
| QO6 | Maintainability index, every file | ≥ 65 | min 39.8, avg 76.5 | ❌ FAIL |
| QO5 | Docstrings + type hints | 100% | 100.0% (lowest category) | ✅ PASS |

Files analysed: 70 · functions/methods: 532 · lines: 8,158

## QO6: Complexity and maintainability per file

| File | Lines | Funcs | Avg CC | Worst function (CC) | MI | MI rank |
|------|------:|------:|-------:|---------------------|---:|:-------:|
| `config/__init__.py` | 5 | 0 | 0.00 | - (0) | 100.0 | A |
| `config/config_loader.py` | 325 | 15 | 3.27 | _value_errors (8) | 56.1 ⚠ | A |
| `core/__init__.py` | 5 | 0 | 0.00 | - (0) | 100.0 | A |
| `core/constants.py` | 68 | 0 | 0.00 | - (0) | 100.0 | A |
| `core/database.py` | 241 | 13 | 2.15 | Database.transaction (5) | 62.2 ⚠ | A |
| `core/exceptions.py` | 49 | 2 | 1.00 | AppError.__init__ (1) | 100.0 | A |
| `core/logger.py` | 231 | 10 | 2.00 | ActivityLogger.log (4) | 70.9 | A |
| `core/settings_manager.py` | 235 | 20 | 1.80 | SettingsManager.seed_defaults (5) | 63.9 ⚠ | A |
| `models/__init__.py` | 30 | 0 | 0.00 | - (0) | 100.0 | A |
| `models/activity_log.py` | 57 | 3 | 2.00 | ActivityLog.details (4) | 82.8 | A |
| `models/category.py` | 43 | 2 | 1.00 | Category.from_row (1) | 92.0 | A |
| `models/common.py` | 84 | 5 | 1.60 | row_to_kwargs (3) | 76.8 | A |
| `models/filters.py` | 46 | 0 | 0.00 | - (0) | 78.3 | A |
| `models/product.py` | 105 | 7 | 1.71 | Product.status (4) | 71.9 | A |
| `models/reports.py` | 61 | 0 | 0.00 | - (0) | 82.3 | A |
| `models/setting.py` | 41 | 2 | 1.00 | Setting.from_row (1) | 100.0 | A |
| `models/stock_transaction.py` | 56 | 3 | 1.00 | StockTransaction.from_row (1) | 83.9 | A |
| `models/supplier.py` | 49 | 2 | 1.00 | Supplier.from_row (1) | 89.9 | A |
| `repositories/__init__.py` | 5 | 0 | 0.00 | - (0) | 100.0 | A |
| `repositories/activity_log_repository.py` | 141 | 9 | 2.22 | ActivityLogRepository._filters (8) | 72.0 | A |
| `repositories/base.py` | 97 | 8 | 1.38 | BaseRepository.where (2) | 78.5 | A |
| `repositories/category_repository.py` | 105 | 8 | 1.50 | CategoryRepository.get (2) | 79.4 | A |
| `repositories/product_repository.py` | 196 | 15 | 1.93 | ProductRepository._filters (5) | 64.8 ⚠ | A |
| `repositories/settings_repository.py` | 45 | 4 | 1.50 | SettingsRepository.all_values (2) | 100.0 | A |
| `repositories/stock_transaction_repository.py` | 167 | 10 | 2.40 | StockTransactionRepository._filters (8) | 69.9 | A |
| `repositories/supplier_repository.py` | 94 | 7 | 1.86 | SupplierRepository.update (3) | 67.3 | A |
| `services/__init__.py` | 5 | 0 | 0.00 | - (0) | 100.0 | A |
| `services/activity_service.py` | 165 | 12 | 1.50 | ActivityService.record_error (4) | 74.1 | A |
| `services/category_service.py` | 115 | 9 | 1.56 | CategoryService._ensure_unique (3) | 76.3 | A |
| `services/container.py` | 99 | 1 | 1.00 | build_services (1) | 100.0 | A |
| `services/product_service.py` | 265 | 19 | 1.89 | ProductService._ensure_unique_sku (4) | 58.1 ⚠ | A |
| `services/report_service.py` | 238 | 15 | 1.87 | ReportService.turnover_report (3) | 59.8 ⚠ | A |
| `services/settings_service.py` | 163 | 16 | 1.44 | SettingsService.save (5) | 69.2 | A |
| `services/stock_service.py` | 244 | 10 | 2.10 | StockService._apply (4) | 64.1 ⚠ | A |
| `services/supplier_service.py` | 121 | 9 | 1.44 | _audit (2) | 82.3 | A |
| `services/system_service.py` | 132 | 7 | 1.57 | _describe (3) | 76.9 | A |
| `ui/__init__.py` | 5 | 0 | 0.00 | - (0) | 100.0 | A |
| `ui/app.py` | 206 | 14 | 1.86 | App._on_setting_changed (5) | 53.1 ⚠ | A |
| `ui/components/__init__.py` | 5 | 0 | 0.00 | - (0) | 100.0 | A |
| `ui/components/chart_panel.py` | 95 | 5 | 1.80 | ChartPanel._style (4) | 77.7 | A |
| `ui/components/confirm_dialog.py` | 74 | 4 | 1.25 | ConfirmDialog.__init__ (2) | 100.0 | A |
| `ui/components/data_table.py` | 193 | 13 | 2.54 | DataTable.set_rows (4) | 56.8 ⚠ | A |
| `ui/components/form_dialog.py` | 172 | 8 | 2.88 | FormDialog._make_input (7) | 63.2 ⚠ | A |
| `ui/components/messages.py` | 32 | 3 | 1.00 | show_warning (1) | 100.0 | A |
| `ui/components/stat_card.py` | 47 | 2 | 1.50 | StatCard.set (2) | 92.0 | A |
| `ui/components/status_bar.py` | 63 | 4 | 1.25 | StatusBar.show (2) | 84.6 | A |
| `ui/components/toolbar.py` | 81 | 5 | 2.00 | Toolbar.add_button (3) | 78.7 | A |
| `ui/components/window_utils.py` | 26 | 1 | 1.00 | center_on_parent (1) | 89.6 | A |
| `ui/theme.py` | 119 | 13 | 1.38 | Theme.font (2) | 69.0 | A |
| `ui/views/__init__.py` | 5 | 0 | 0.00 | - (0) | 100.0 | A |
| `ui/views/about.py` | 104 | 6 | 2.00 | AboutView.refresh (5) | 66.9 | A |
| `ui/views/activity_log.py` | 237 | 18 | 2.50 | summarize (8) | 42.5 ⚠ | A |
| `ui/views/base_view.py` | 143 | 13 | 1.54 | BaseView.form_call (4) | 74.4 | A |
| `ui/views/categories.py` | 62 | 6 | 1.17 | CategoriesView.save (2) | 78.2 | A |
| `ui/views/crud_view.py` | 182 | 22 | 1.55 | CrudView._delete_selected (4) | 57.8 ⚠ | A |
| `ui/views/dashboard.py` | 178 | 11 | 2.64 | DashboardView.refresh (6) | 50.4 ⚠ | A |
| `ui/views/products.py` | 198 | 18 | 1.94 | _tags (4) | 48.9 ⚠ | A |
| `ui/views/reports.py` | 220 | 17 | 2.59 | ReportsView.refresh (6) | 44.2 ⚠ | A |
| `ui/views/settings.py` | 126 | 10 | 2.20 | SettingsView._make_input (4) | 61.7 ⚠ | A |
| `ui/views/stock.py` | 276 | 21 | 2.38 | StockView._load_products (7) | 39.8 ⚠ | A |
| `ui/views/suppliers.py` | 67 | 6 | 1.17 | SuppliersView.save (2) | 77.5 | A |
| `utils/__init__.py` | 5 | 0 | 0.00 | - (0) | 100.0 | A |
| `utils/csv_export.py` | 42 | 2 | 3.00 | write_csv (5) | 93.0 | A |
| `utils/date_helpers.py` | 51 | 8 | 1.25 | days_ago (2) | 79.6 | A |
| `utils/formatters.py` | 79 | 8 | 2.62 | _parse_timestamp (4) | 76.2 | A |
| `utils/validators.py` | 157 | 13 | 3.23 | Validator.text (6) | 57.3 ⚠ | A |
| `scripts/doc_coverage.py` | 194 | 14 | 3.36 | _fully_annotated (7) | 48.6 ⚠ | A |
| `scripts/quality_report.py` | 186 | 9 | 5.44 | render (10) | 50.9 ⚠ | A |
| `scripts/seed_data.py` | 335 | 13 | 3.38 | receive_orders (6) | 46.2 ⚠ | A |
| `main.py` | 65 | 2 | 2.00 | _fail (2) | 89.6 | A |

## Refactoring candidates

- `config/config_loader.py`: MI 56.1 below 65
- `core/database.py`: MI 62.2 below 65
- `core/settings_manager.py`: MI 63.9 below 65
- `repositories/product_repository.py`: MI 64.8 below 65
- `services/product_service.py`: MI 58.1 below 65
- `services/report_service.py`: MI 59.8 below 65
- `services/stock_service.py`: MI 64.1 below 65
- `ui/app.py`: MI 53.1 below 65
- `ui/components/data_table.py`: MI 56.8 below 65
- `ui/components/form_dialog.py`: MI 63.2 below 65
- `ui/views/activity_log.py`: MI 42.5 below 65
- `ui/views/crud_view.py`: MI 57.8 below 65
- `ui/views/dashboard.py`: MI 50.4 below 65
- `ui/views/products.py`: MI 48.9 below 65
- `ui/views/reports.py`: MI 44.2 below 65
- `ui/views/settings.py`: MI 61.7 below 65
- `ui/views/stock.py`: MI 39.8 below 65
- `utils/validators.py`: MI 57.3 below 65
- `scripts/doc_coverage.py`: MI 48.6 below 65
- `scripts/quality_report.py`: MI 50.9 below 65
- `scripts/seed_data.py`: MI 46.2 below 65

<!-- DOC_COVERAGE:START -->
## QO5: Documented code (docstrings and type hints)

**Verdict: ✅ PASS** (target: 100% for every row)

| Item | Documented | Total | Coverage |
|------|-----------:|------:|---------:|
| Modules (header docstring) | 70 | 70 | 100.0% |
| Classes | 74 | 74 | 100.0% |
| Public functions & methods | 349 | 349 | 100.0% |
| Functions fully type-hinted | 532 | 532 | 100.0% |

Files analysed: 70. Gaps found: 0.

<!-- DOC_COVERAGE:END -->
