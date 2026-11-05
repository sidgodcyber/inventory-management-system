# Quality report: maintainability evidence (Q11)

Generated 2026-11-05 18:23 by `scripts/quality_report.py` (radon CC + MI, docstring coverage). **Do not edit by hand.**

Scope: QO6 is judged on the application (`config`, `core`, `models`, `repositories`, `services`, `ui`, `utils`, `main.py`). Developer tooling in `scripts/` is listed for information; QO5 covers both.

## Summary

| Objective | Measure | Target | Result | Verdict |
|-----------|---------|--------|--------|---------|
| QO6 | Average cyclomatic complexity | ≤ 5 (grade A) | 1.95 (grade A) | ✅ PASS |
| QO6 | Maintainability index, every file | ≥ 65 | min 65.2, avg 81.4 | ✅ PASS |
| QO5 | Docstrings + type hints | 100% | 100.0% (lowest category) | ✅ PASS |
| QO7 | pytest (repositories, services, utils, config, core) | all pass | 180 passed in 29.92s | ✅ PASS |

Files analysed: 104 · functions/methods: 591 · lines: 10,217

## QO6: Complexity and maintainability per application file

| File | Lines | Funcs | Avg CC | Worst function (CC) | MI | MI rank |
|------|------:|------:|-------:|---------------------|---:|:-------:|
| `config/__init__.py` | 5 | 0 | 0.00 | - (0) | 100.0 | A |
| `config/config_loader.py` | 139 | 8 | 1.88 | _read_json (3) | 71.9 | A |
| `config/schema.py` | 113 | 0 | 0.00 | - (0) | 89.9 | A |
| `config/validation.py` | 128 | 7 | 4.86 | value_errors (8) | 69.0 | A |
| `core/__init__.py` | 5 | 0 | 0.00 | - (0) | 100.0 | A |
| `core/constants.py` | 76 | 0 | 0.00 | - (0) | 100.0 | A |
| `core/database.py` | 175 | 12 | 2.25 | Database.transaction (6) | 65.4 | A |
| `core/exceptions.py` | 57 | 2 | 1.00 | AppError.__init__ (1) | 100.0 | A |
| `core/logger.py` | 231 | 10 | 2.00 | ActivityLogger.log (4) | 70.9 | A |
| `core/schema.py` | 126 | 1 | 2.00 | _sql_list (2) | 100.0 | A |
| `core/setting_definitions.py` | 87 | 2 | 2.50 | serialize (3) | 90.6 | A |
| `core/settings_manager.py` | 165 | 18 | 1.72 | SettingsManager.seed_defaults (5) | 67.1 | A |
| `models/__init__.py` | 32 | 0 | 0.00 | - (0) | 100.0 | A |
| `models/activity_log.py` | 57 | 3 | 2.00 | ActivityLog.details (4) | 82.8 | A |
| `models/category.py` | 43 | 2 | 1.00 | Category.from_row (1) | 92.0 | A |
| `models/common.py` | 84 | 5 | 1.60 | row_to_kwargs (3) | 76.8 | A |
| `models/filters.py` | 46 | 0 | 0.00 | - (0) | 78.3 | A |
| `models/movement.py` | 30 | 1 | 1.00 | MovementResult.low_stock_alert (1) | 100.0 | A |
| `models/product.py` | 105 | 7 | 1.71 | Product.status (4) | 71.9 | A |
| `models/reports.py` | 61 | 0 | 0.00 | - (0) | 82.3 | A |
| `models/setting.py` | 41 | 2 | 1.00 | Setting.from_row (1) | 100.0 | A |
| `models/stock_transaction.py` | 56 | 3 | 1.00 | StockTransaction.from_row (1) | 83.9 | A |
| `models/supplier.py` | 49 | 2 | 1.00 | Supplier.from_row (1) | 89.9 | A |
| `models/user.py` | 68 | 3 | 1.00 | User.from_row (1) | 84.2 | A |
| `repositories/__init__.py` | 5 | 0 | 0.00 | - (0) | 100.0 | A |
| `repositories/activity_log_repository.py` | 141 | 9 | 2.22 | ActivityLogRepository._filters (8) | 72.0 | A |
| `repositories/base.py` | 97 | 8 | 1.38 | BaseRepository.where (2) | 78.5 | A |
| `repositories/category_repository.py` | 105 | 8 | 1.50 | CategoryRepository.get (2) | 79.4 | A |
| `repositories/product_repository.py` | 255 | 15 | 1.93 | ProductRepository._filters (5) | 70.9 | A |
| `repositories/settings_repository.py` | 45 | 4 | 1.50 | SettingsRepository.all_values (2) | 100.0 | A |
| `repositories/stock_transaction_repository.py` | 167 | 10 | 2.40 | StockTransactionRepository._filters (8) | 69.9 | A |
| `repositories/supplier_repository.py` | 94 | 7 | 1.86 | SupplierRepository.update (3) | 67.3 | A |
| `repositories/user_repository.py` | 102 | 10 | 1.30 | UserRepository.get (2) | 78.1 | A |
| `services/__init__.py` | 5 | 0 | 0.00 | - (0) | 100.0 | A |
| `services/activity_service.py` | 166 | 11 | 1.55 | ActivityService.record_error (4) | 73.7 | A |
| `services/auth_service.py` | 164 | 9 | 3.00 | AuthService.login (10) | 66.1 | A |
| `services/category_service.py` | 123 | 9 | 1.56 | CategoryService._ensure_unique (3) | 75.1 | A |
| `services/container.py` | 110 | 1 | 1.00 | build_services (1) | 100.0 | A |
| `services/password_policy.py` | 77 | 4 | 1.75 | PasswordPolicy.check_change (3) | 74.8 | A |
| `services/permissions.py` | 61 | 1 | 1.00 | permissions_for (1) | 93.9 | A |
| `services/product_service.py` | 260 | 12 | 1.67 | ProductService.delete (3) | 69.2 | A |
| `services/product_validation.py` | 148 | 8 | 2.12 | ProductFormParser.ensure_unique_sku (4) | 73.7 | A |
| `services/report_service.py` | 203 | 12 | 1.67 | ReportService._turnover_frame (3) | 69.1 | A |
| `services/settings_service.py` | 165 | 16 | 1.44 | SettingsService.save (5) | 69.0 | A |
| `services/stock_service.py` | 249 | 9 | 2.22 | StockService._apply (4) | 65.4 | A |
| `services/supplier_service.py` | 129 | 9 | 1.44 | _audit (2) | 81.3 | A |
| `services/system_service.py` | 132 | 7 | 1.57 | _describe (3) | 76.9 | A |
| `services/turnover.py` | 149 | 7 | 1.86 | to_rows (3) | 72.4 | A |
| `services/user_service.py` | 170 | 8 | 2.50 | UserService.set_active (6) | 68.4 | A |
| `ui/__init__.py` | 5 | 0 | 0.00 | - (0) | 100.0 | A |
| `ui/app.py` | 206 | 15 | 1.60 | App._on_setting_changed (4) | 65.2 | A |
| `ui/components/__init__.py` | 5 | 0 | 0.00 | - (0) | 100.0 | A |
| `ui/components/chart_panel.py` | 95 | 5 | 1.80 | ChartPanel._style (4) | 77.7 | A |
| `ui/components/confirm_dialog.py` | 74 | 4 | 1.25 | ConfirmDialog.__init__ (2) | 100.0 | A |
| `ui/components/data_table.py` | 173 | 11 | 2.64 | DataTable.__init__ (4) | 66.1 | A |
| `ui/components/form_dialog.py` | 126 | 7 | 2.14 | FormDialog._add_field (4) | 70.5 | A |
| `ui/components/form_fields.py` | 89 | 2 | 4.50 | make_input (7) | 78.5 | A |
| `ui/components/messages.py` | 32 | 3 | 1.00 | show_warning (1) | 100.0 | A |
| `ui/components/pager.py` | 52 | 2 | 2.50 | Pager.update_page (4) | 82.8 | A |
| `ui/components/product_picker.py` | 94 | 5 | 3.00 | ProductPicker.set_products (6) | 77.4 | A |
| `ui/components/sidebar.py` | 98 | 5 | 2.40 | Sidebar.highlight (4) | 78.3 | A |
| `ui/components/stat_card.py` | 47 | 2 | 1.50 | StatCard.set (2) | 92.0 | A |
| `ui/components/status_bar.py` | 63 | 4 | 1.25 | StatusBar.show (2) | 84.6 | A |
| `ui/components/table_types.py` | 40 | 0 | 0.00 | - (0) | 100.0 | A |
| `ui/components/toolbar.py` | 75 | 5 | 1.60 | Toolbar.__init__ (2) | 82.4 | A |
| `ui/components/window_utils.py` | 44 | 2 | 1.00 | fit_to_screen (1) | 82.9 | A |
| `ui/navigation.py` | 57 | 0 | 0.00 | - (0) | 92.8 | A |
| `ui/session.py` | 95 | 5 | 2.60 | allowed_screens (4) | 78.1 | A |
| `ui/theme.py` | 135 | 14 | 1.50 | Theme.button_style (3) | 67.7 | A |
| `ui/views/__init__.py` | 5 | 0 | 0.00 | - (0) | 100.0 | A |
| `ui/views/about.py` | 104 | 6 | 2.00 | AboutView.refresh (5) | 66.9 | A |
| `ui/views/activity_details.py` | 45 | 2 | 2.00 | ActivityDetails.show (3) | 90.4 | A |
| `ui/views/activity_filters.py` | 90 | 4 | 2.00 | ActivityFilterBar.clear (3) | 84.6 | A |
| `ui/views/activity_log.py` | 160 | 12 | 2.00 | ActivityLogView._purge (5) | 65.7 | A |
| `ui/views/activity_summary.py` | 40 | 2 | 5.50 | summarize (8) | 85.6 | A |
| `ui/views/base_view.py` | 154 | 14 | 1.50 | BaseView.form_call (4) | 74.2 | A |
| `ui/views/categories.py` | 62 | 6 | 1.17 | CategoriesView.save (2) | 78.2 | A |
| `ui/views/change_password.py` | 52 | 1 | 3.00 | ask_new_password (3) | 100.0 | A |
| `ui/views/crud_view.py` | 189 | 17 | 1.71 | CrudView._delete_selected (4) | 67.5 | A |
| `ui/views/dashboard.py` | 102 | 5 | 2.40 | DashboardView.refresh (6) | 68.5 | A |
| `ui/views/dashboard_cards.py` | 61 | 2 | 3.00 | KpiCards.__init__ (3) | 90.8 | A |
| `ui/views/dashboard_charts.py` | 91 | 4 | 2.75 | draw_value_bars (5) | 78.9 | A |
| `ui/views/history_filters.py` | 100 | 5 | 2.20 | HistoryFilterBar.__init__ (4) | 82.6 | A |
| `ui/views/list_view.py` | 140 | 14 | 1.14 | ListView.load_page (3) | 80.4 | A |
| `ui/views/login.py` | 75 | 3 | 2.33 | LoginView.submit (3) | 83.5 | A |
| `ui/views/product_form.py` | 91 | 5 | 2.00 | ProductForm.load_lookups (3) | 84.7 | A |
| `ui/views/products.py` | 199 | 16 | 1.88 | _tags (4) | 65.6 | A |
| `ui/views/report_period.py` | 90 | 6 | 2.17 | PeriodBar.read (4) | 76.1 | A |
| `ui/views/report_reorder.py` | 59 | 3 | 2.33 | _row (3) | 89.1 | A |
| `ui/views/report_turnover.py` | 81 | 4 | 3.25 | TurnoverPanel.show (6) | 76.6 | A |
| `ui/views/reports.py` | 117 | 8 | 2.50 | ReportsView.refresh (5) | 70.5 | A |
| `ui/views/settings.py` | 159 | 10 | 2.30 | SettingsView._make_input (4) | 71.1 | A |
| `ui/views/stock.py` | 137 | 10 | 1.60 | StockView._load_products (3) | 73.0 | A |
| `ui/views/stock_movement.py` | 108 | 5 | 3.00 | MovementPanel._movement_changed (4) | 71.7 | A |
| `ui/views/suppliers.py` | 67 | 6 | 1.17 | SuppliersView.save (2) | 77.5 | A |
| `ui/views/users.py` | 129 | 9 | 2.56 | UsersView._toggle_active (7) | 66.1 | A |
| `utils/__init__.py` | 5 | 0 | 0.00 | - (0) | 100.0 | A |
| `utils/csv_export.py` | 42 | 2 | 3.00 | write_csv (5) | 93.0 | A |
| `utils/date_helpers.py` | 95 | 10 | 1.70 | is_valid_strftime (4) | 76.8 | A |
| `utils/formatters.py` | 79 | 8 | 2.62 | _parse_timestamp (4) | 76.2 | A |
| `utils/parsing.py` | 103 | 4 | 4.50 | parse_int (7) | 67.4 | A |
| `utils/passwords.py` | 60 | 3 | 1.67 | verify_password (3) | 88.5 | A |
| `utils/validators.py` | 155 | 10 | 2.00 | Validator.text (6) | 69.3 | A |
| `main.py` | 65 | 2 | 2.00 | _fail (2) | 90.0 | A |

## Refactoring candidates

None: no function above CC 10 and every file has MI ≥ 65.

## Developer tooling (informational, not judged)

| File | Lines | Funcs | Avg CC | Worst function (CC) | MI | MI rank |
|------|------:|------:|-------:|---------------------|---:|:-------:|
| `scripts/doc_coverage.py` | 201 | 15 | 3.33 | _fully_annotated (7) | 48.1 ⚠ | A |
| `scripts/quality_report.py` | 194 | 9 | 5.56 | render (10) | 50.0 ⚠ | A |
| `scripts/seed_data.py` | 357 | 15 | 3.20 | receive_orders (6) | 45.2 ⚠ | A |

<!-- DOC_COVERAGE:START -->
## QO5: Documented code (docstrings and type hints)

**Verdict: ✅ PASS** (target: 100% for every row)

| Item | Documented | Total | Coverage |
|------|-----------:|------:|---------:|
| Modules (header docstring) | 107 | 107 | 100.0% |
| Classes | 97 | 97 | 100.0% |
| Public functions & methods | 473 | 473 | 100.0% |
| Functions fully type-hinted | 632 | 632 | 100.0% |

Files analysed: 107. Gaps found: 0.

<!-- DOC_COVERAGE:END -->
