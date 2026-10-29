# Software Requirements Specification
## Inventory Management System — Quality Goal Q11: Improve Maintainability

| | |
|---|---|
| Course | BBAT104 — Fundamentals of TQM (B.Tech CSE AI&ML, 5th semester, Amrapali University) |
| Author | Siddhi Baluja, Roll/Reg No 240302054 |
| Version | 1.0 |

---

## 1. Introduction

### 1.1 Purpose
This document specifies a desktop Inventory Management System (IMS) for a small store. The system serves the baseline TQM goal of **eliminating stockouts and tracking the inventory turnover rate**, and it is engineered to satisfy the assigned quality goal **Q11: Improve Maintainability**.

### 1.2 Problem statement
Small stores that track stock on paper or spreadsheets discover stockouts only when a customer asks for an item. They cannot say which products tie up capital or move slowly, and they cannot trace who changed a figure. Ad-hoc software built to fix this tends to accumulate hard-coded values and untraceable changes, so it becomes costly to change. Both problems are quality failures. The first hurts customers; the second hurts the team that maintains the system.

### 1.3 Scope
In scope: categories, suppliers and products (CRUD); stock in, stock out and adjustments with history; low-stock alerts; turnover and days-of-stock reports; a dashboard; CSV export; runtime settings; an audit trail; and maintainability evidence (tests, complexity, documentation coverage).
Out of scope: multi-user authentication, purchase-order workflow, barcode hardware, networked or multi-store use.

### 1.4 Definitions
| Term | Meaning |
|---|---|
| SKU | Stock-keeping unit code, unique per product |
| Reorder level | Stock quantity at or below which a product is "low stock" |
| Stockout | Quantity on hand = 0 |
| COGS | Cost of goods sold = Σ (OUT quantity × unit cost) in a period |
| Turnover | COGS ÷ average inventory value for the period |
| Days of stock | Quantity on hand ÷ average daily usage |
| MI / CC | Maintainability index / cyclomatic complexity (radon) |

## 2. Overall description

### 2.1 Product perspective
A standalone Python 3.10+ desktop application. It uses a CustomTkinter UI, a single SQLite file, and Pandas/Matplotlib for analytics. The code is layered as UI → services → repositories → core (see `docs/architecture.md`).

### 2.2 User roles
The app has a single login. The current operator's name and role are runtime settings and are recorded on every audit entry.

| Role | Typical tasks |
|---|---|
| Admin / Store Manager | Maintain products, categories and suppliers; change settings; review reports and the activity log; purge old log entries |
| Store Staff | Record stock in, stock out and adjustments; view the dashboard and products |

### 2.3 Assumptions and constraints
- **A1.** One operator uses the application at a time on one computer.
- **A2.** Stock valuation uses each product's current unit cost.
- **C1.** The mandatory stack is Python, CustomTkinter, SQLite3, Pandas, Matplotlib, pytest and radon. No web frameworks and no ORM.
- **C2.** All tunable values must come from `config/config.json` or the `settings` table.
- **C3.** The window must be usable at a minimum of about 1200×720, and smaller screens are clamped to fit.

## 3. Functional requirements

| ID | Requirement |
|---|---|
| FR-01 | The system shall create, view, update, search, sort and paginate **categories**. A category used by any product cannot be deleted. |
| FR-02 | The system shall create, view, update, delete, search, sort and paginate **suppliers**, validating email and phone formats. |
| FR-03 | The system shall create, view, update, search (SKU, name, category, supplier), sort and paginate **products**, with category, low-stock-only and include-inactive filters. |
| FR-04 | SKUs shall be unique (case-insensitive) and match the configured pattern. Cost and price must be ≥ 0, and a price below cost produces a warning. |
| FR-05 | A product with stock history shall be **soft-deleted** (deactivated) and restorable. A product without history is deleted permanently. |
| FR-06 | **Stock in** shall add stock and record the quantity, unit cost and a reference. Opening stock is booked as a stock-in. |
| FR-07 | **Stock out** shall never make quantity on hand negative. An over-issue is refused with an explanation. |
| FR-08 | **Adjustment** shall set stock to a counted quantity, require a reason and store the signed difference. |
| FR-09 | Quantity on hand shall change **only** through FR-06 to FR-08, each atomic with its transaction row and audit entry. |
| FR-10 | Transaction history shall be filterable by product, type and date range, and sortable, paginated and exportable to CSV. |
| FR-11 | Products at or below their reorder level shall be highlighted red (stockouts darker), counted on a sidebar badge, listed on the dashboard and toasted after a movement. |
| FR-12 | The system shall report **turnover** and **days of stock** per product and store-wide for a chosen period, exportable to CSV. |
| FR-13 | The **dashboard** shall show total products, stock value, low-stock count, stockouts, turnover, stock value by category (chart), units in vs out over the last N days (chart) and the reorder list. |
| FR-14 | The product list, transaction history, turnover report, reorder list and activity log shall export to CSV. |
| FR-15 | A **Settings** screen shall edit the runtime settings: appearance, currency, default reorder level, page size, date format, log level, log retention, operator name and role. It shall save, revert and reset to `config.json` defaults, and apply changes without a restart. |
| FR-16 | Every create, update, delete, stock movement, settings change, export, login and caught error shall be written to the **activity log** with user, timestamp, entity, id, old→new values and level. |
| FR-17 | An **Activity Log** screen shall filter by date range, action, entity and user, search details, show full details, export to CSV and purge entries older than the retention period after confirmation. |
| FR-18 | Technical events shall be written to a **rotating log file** (`logs/app.log`) at the configured level. |
| FR-19 | An **About / Architecture** screen shall show app identity, paths, schema version, the layer diagram and rules, and a live module inventory. |
| FR-20 | Errors shall be shown as friendly dialogs or inline form messages and never as raw tracebacks. |

## 4. Non-functional requirements (maintainability, mapped to the quality objectives)

| NFR | Requirement | QO | Verification |
|---|---|---|---|
| NFR-01 | UI never runs SQL; each layer talks only to the layer below | QO1 | Folder structure, `docs/architecture.md`, code review |
| NFR-02 | Zero hard-coded configuration (paths, thresholds, theme, page size, currency, log level, colours, fonts) | QO2 | `config/config.json` + `config/schema.py` validation |
| NFR-03 | Low-stock default, theme, currency, page size, date format and log level changeable at runtime | QO3 | Settings screen demo |
| NFR-04 | 100% of business actions traceable (user, time, entity, old→new) | QO4 | Activity Log screen, `logs/app.log` |
| NFR-05 | 100% docstrings for modules, classes and public functions; full type hints | QO5 | `scripts/doc_coverage.py` |
| NFR-06 | Average CC grade A (≤ 5); MI ≥ 65 for every application file | QO6 | `scripts/quality_report.py` |
| NFR-07 | Repository and service layers covered by automated tests, all passing | QO7 | `pytest` |
| NFR-08 | A broken `config.json` stops start-up with a message listing every problem | QO2 | `tests/test_config_loader.py` |
| NFR-09 | Data and audit trail commit atomically; stock never negative (DB `CHECK` + service rule) | QO4 | `tests/test_stock_product_services.py` |

## 5. Critical-to-Quality (CTQ) parameters

| Customer need | Driver | CTQ (measurable) | Target |
|---|---|---|---|
| Products are on the shelf | Low-stock visibility | Stockout count (dashboard) | 0 |
| | | Low-stock items without a reorder | Trend → 0 |
| Capital is not tied up | Turnover tracking | Inventory turnover per period | Rising trend; days of stock ≤ 30 for fast movers |
| Stock figures are trusted | Traceability | Movements without an audit entry | 0 (enforced atomically) |
| | Data accuracy | Negative-stock events | 0 (enforced) |
| System is cheap to change | Maintainability | Avg CC / min MI / doc coverage / failing tests | ≤ 5 / ≥ 65 / 100% / 0 |

**Formulas:** COGS = Σ OUT qty × unit cost; average inventory = mean of the daily closing stock × unit cost; turnover = COGS ÷ average inventory; days of stock = on hand ÷ (units issued ÷ days).

## 6. Data dictionary

| Table.column | Type | Rules |
|---|---|---|
| categories.name | TEXT | Required, unique (case-insensitive), ≤ 120 chars |
| suppliers.email / phone | TEXT | Optional; configured regex patterns |
| products.sku | TEXT | Required, unique (case-insensitive), `^[A-Z0-9][A-Z0-9-]{1,19}$` |
| products.unit | TEXT | One of `inventory.units` in config |
| products.unit_cost / selling_price | REAL | ≥ 0, 2 decimals |
| products.quantity_on_hand | INTEGER | ≥ 0 (`CHECK`); changed only by stock transactions |
| products.reorder_level | INTEGER | 0 … `validation.reorder_level_max` |
| products.is_active | INTEGER | 1 active, 0 soft-deleted |
| stock_transactions.type | TEXT | `IN`, `OUT`, `ADJUST` (`CHECK`) |
| stock_transactions.quantity | INTEGER | > 0 for IN/OUT; signed delta ≠ 0 for ADJUST |
| activity_log.action | TEXT | `CREATE, UPDATE, DELETE, STOCK_IN, STOCK_OUT, ADJUST, SETTINGS_CHANGE, LOGIN, EXPORT, ERROR` |
| activity_log.details_json | TEXT | JSON: `{"new":…}`, `{"old":…}`, `{"changes":{field:{old,new}}}`, or error context |
| activity_log.level | TEXT | `DEBUG … CRITICAL` |
| settings.value_type | TEXT | `str`, `int`, `float`, `bool` |
| *all* created_at / timestamp | TEXT | `YYYY-MM-DD HH:MM:SS` local time |
