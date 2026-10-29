# User Manual — Inventory Management System

This manual walks through each screen of the app, from first start to exporting reports.

## Getting started

```bash
pip install -r requirements.txt
python scripts/seed_data.py        # optional: 40 products and 90 days of sample history
python main.py
```

The window opens on the **Dashboard**. Use the sidebar to switch screens. The status bar at the bottom shows short confirmations on the left, and the operator, role, database file and version on the right. The red number on **Products** counts products at or below their reorder level.

If `config/config.json` is broken, the app does not start. It shows a message listing every problem; fix the file and start again.

## Dashboard
- **Cards:** active products, stock value at cost, low-stock count, stockouts, and inventory turnover for the configured period (90 days by default).
- **Stock value by category:** where the money sits.
- **Units in vs out:** daily receipts and issues over the last 30 days.
- **Needs reordering:** every product at or below its reorder level, with the minimum quantity to order. **Open in Products** jumps to the product list filtered to low stock.

## Products
- **Search** by SKU, name, category or supplier as you type. Click a column header to sort, and use **‹ Prev / Next ›** to page. Page size is a setting.
- **Filters:** category, *Low stock only*, *Show inactive*.
- **Colours:** red row = at or below reorder level; dark red = out of stock; grey text = deactivated.
- **+ Add product:** SKU (letters, digits and dashes), name, category, optional supplier, unit, cost, price, reorder level (pre-filled from settings) and optional opening stock, which is booked as a stock-in. Mistakes are shown in red inside the dialog. A price below cost saves, but shows a warning.
- **Edit:** double-click a row or select it and press **Edit**. Quantity cannot be edited here; use the Stock screen.
- **Delete:** a product with stock history is *deactivated* rather than deleted. Tick *Show inactive*, select it and press **Restore** to bring it back.
- **Export CSV** saves the list to the `exports/` folder.

## Categories and Suppliers
Both screens work like Products: search, sort, page, add, edit and delete. A category or supplier that is still used by a product cannot be deleted; move those products first. Supplier email and phone formats are checked.

## Stock
1. **Choose a product:** type its SKU or pick it from the list. The line next to it shows on-hand quantity, reorder level and cost.
2. **Choose the movement:**
   - **Stock In:** quantity received and optional unit cost (defaults to the product cost) and invoice reference.
   - **Stock Out:** quantity issued. You cannot issue more than is in stock.
   - **Adjust:** enter the **counted** quantity and a **reason** (damage, recount, expiry). The difference is recorded.
3. Press **Record movement**. If the product is now at or below its reorder level, the confirmation turns amber.

**History** lists every movement, newest first: green for IN, amber for ADJUST. Filter by product, type and a date range (use the date format shown in the boxes), then **Apply**. **Clear** resets the filters, and **Export CSV** saves the filtered list.

## Reports
- Pick **30 / 90 / 180 days** or type custom dates and press **Run report**.
- The summary line shows the store-wide turnover, COGS and average inventory value for the period.
- **Inventory turnover** tab: one row per product with units issued, COGS, average inventory, turnover, usage per day and days of stock. Amber rows will run out within the warning window (7 days by default); red rows are already out. Click headers to sort.
- **Reorder list** tab: products needing reorder.
- Each tab has its own **Export CSV** button.

## Activity Log
Every action is recorded here with the time, operator, action, entity, record ID and a summary such as `name: Pen → Gel pen` or `qty 5: 20 → 15`.
- **Filter** by date range, action, entity and user, then **Apply**. The search box looks inside the details.
- **Select a row** to see its full details (old and new values, or the error context) in the pane below.
- **ERROR** rows (red, or amber for user mistakes such as an over-issue) are the raw data for the TQM defect checksheet.
- **Export CSV** saves the filtered entries.
- **Purge old entries** deletes entries older than the retention setting after you confirm. The purge itself is logged.

The technical log is written to `logs/app.log` and rotates automatically.

## Settings
Each setting shows a description and its default from `config/config.json`.

| Setting | Effect |
|---|---|
| Appearance mode | light / dark / system: applies instantly |
| Currency symbol | Used in every money column and export |
| Default reorder level | Pre-filled for new products |
| Rows per page | Every paginated table |
| Date format | Display and typing of dates (e.g. `%d-%m-%Y`) |
| Log level | Minimum level written to `logs/app.log`: applies instantly |
| Activity-log retention | Age (days) after which entries can be purged |
| Operator name / role | Shown in the status bar and recorded on every action |

Press **Save changes** to apply. Every value is checked first, and if one is invalid nothing is saved. **Revert** discards unsaved edits. **Reset to defaults** restores `config.json` values after you confirm. Every change appears in the Activity Log as `SETTINGS_CHANGE` with its old and new value.

## About
The **Overview** tab shows the version, author, file locations, schema version, where each Q11 feature lives, the layer diagram and the rules the code follows. The **Modules** tab lists every source module with its purpose, read live from the code.

## Maintenance commands

```bash
python -m pytest                           # run the automated tests
python scripts/quality_report.py --tests   # regenerate docs/quality_report.md
python scripts/doc_coverage.py             # docstring / type-hint coverage only
python scripts/seed_data.py --reset        # recreate the sample database
```
