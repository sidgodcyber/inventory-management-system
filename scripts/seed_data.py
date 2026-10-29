"""Seed the database with realistic sample data for demos and TQM analysis.

Creates 6 categories, 5 suppliers and 40 products, then simulates 90 days of
store operation: daily customer demand (stock out), reorders arriving after a
lead time (stock in), occasional cycle-count adjustments and operator shift
changes. A few products are deliberately "neglected" near the end so the
dashboard shows real low-stock and stockout cases, and failed over-issue
attempts are captured as ``ERROR`` activity entries for the defect checksheet.

Everything goes through the service layer, so every seeded movement is
validated and audited exactly like a real one.

Usage::

    python scripts/seed_data.py            # refuses if products already exist
    python scripts/seed_data.py --reset    # delete the database and re-seed

Layer: scripts (composition context, like main.py)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.config_loader import AppConfig, load_config  # noqa: E402
from core.database import Database  # noqa: E402
from core.exceptions import AppError, StockError  # noqa: E402
from core.logger import setup_file_logging  # noqa: E402
from models.common import ListQuery  # noqa: E402
from services.container import AppServices, build_services  # noqa: E402

SIMULATION_DAYS = 90
NEGLECT_FROM_DAY = 74  # neglected products are not reordered after this day
OPERATORS = ("Admin", "Ravi Kumar", "Asha Verma")

CATEGORIES = (
    ("Stationery", "Pens, notebooks, paper and office supplies"),
    ("Electronics", "Computer accessories, cables, batteries and lighting"),
    ("Groceries", "Staple foods and kitchen essentials"),
    ("Cleaning Supplies", "Detergents, cleaners and housekeeping items"),
    ("Personal Care", "Toiletries and hygiene products"),
    ("Hardware", "Tools, fasteners, adhesives and paint"),
)

SUPPLIERS = (
    {"name": "Kumar Stationery Mart", "contact_person": "Rakesh Kumar",
     "phone": "+91 98100 11223", "email": "sales@kumarstationery.in",
     "address": "Sector 18, Noida, Uttar Pradesh"},
    {"name": "TechZone Distributors", "contact_person": "Neha Sharma",
     "phone": "+91 98711 44556", "email": "orders@techzone.co.in",
     "address": "Nehru Place, New Delhi"},
    {"name": "Annapurna Wholesale", "contact_person": "Suresh Gupta",
     "phone": "+91 94120 33445", "email": "supply@annapurna.in",
     "address": "Nainital Road, Haldwani, Uttarakhand"},
    {"name": "CleanPro Supplies", "contact_person": "Pooja Rawat",
     "phone": "+91 99170 55667", "email": "contact@cleanpro.in",
     "address": "Industrial Area, Rudrapur, Uttarakhand"},
    {"name": "BuildRight Hardware", "contact_person": "Manoj Bisht",
     "phone": "+91 97590 77889", "email": "info@buildright.in",
     "address": "Station Road, Kathgodam, Uttarakhand"},
)

# (sku, name, category index, supplier index, unit, cost, price, reorder level, daily demand)
PRODUCTS = (
    ("STA-PEN-001", "Ball Pen Blue (Pack of 10)", 0, 0, "pack", 45, 60, 15, 4),
    ("STA-PEN-002", "Gel Pen Black", 0, 0, "pcs", 12, 20, 30, 8),
    ("STA-NTB-001", "A4 Notebook 200 Pages", 0, 0, "pcs", 55, 80, 20, 5),
    ("STA-NTB-002", "Spiral Notebook A5", 0, 0, "pcs", 35, 50, 20, 3),
    ("STA-PPR-001", "A4 Copier Paper (500 Sheets)", 0, 0, "pack", 260, 340, 10, 2),
    ("STA-STP-001", "Stapler No. 10", 0, 0, "pcs", 85, 130, 5, 0.6),
    ("STA-HLT-001", "Highlighter Set (5 Colours)", 0, 0, "pack", 90, 140, 8, 1),
    ("ELE-USB-001", "USB Flash Drive 32GB", 1, 1, "pcs", 280, 399, 8, 1),
    ("ELE-MSE-001", "Wireless Mouse", 1, 1, "pcs", 350, 549, 6, 0.8),
    ("ELE-KBD-001", "USB Keyboard", 1, 1, "pcs", 420, 650, 5, 0.5),
    ("ELE-CBL-001", "USB-C Charging Cable 1m", 1, 1, "pcs", 90, 199, 15, 3),
    ("ELE-BAT-001", "AA Batteries (Pack of 4)", 1, 1, "pack", 80, 120, 20, 4),
    ("ELE-EXT-001", "Extension Board 4-Socket", 1, 1, "pcs", 260, 399, 6, 0.7),
    ("ELE-LED-001", "LED Bulb 9W", 1, 1, "pcs", 65, 110, 25, 4),
    ("GRO-RCE-001", "Basmati Rice 5kg", 2, 2, "pack", 420, 549, 10, 2),
    ("GRO-ATA-001", "Whole Wheat Atta 10kg", 2, 2, "pack", 360, 450, 10, 2),
    ("GRO-SUG-001", "Sugar 1kg", 2, 2, "kg", 42, 50, 40, 6),
    ("GRO-TEA-001", "Assam Tea 500g", 2, 2, "pack", 210, 280, 12, 2),
    ("GRO-OIL-001", "Sunflower Oil 1L", 2, 2, "litre", 135, 165, 20, 3),
    ("GRO-DAL-001", "Toor Dal 1kg", 2, 2, "kg", 140, 175, 15, 3),
    ("GRO-SLT-001", "Iodised Salt 1kg", 2, 2, "kg", 22, 28, 25, 4),
    ("CLN-DET-001", "Detergent Powder 1kg", 3, 3, "kg", 95, 130, 15, 3),
    ("CLN-DSH-001", "Dishwash Liquid 500ml", 3, 3, "pcs", 85, 115, 15, 2),
    ("CLN-FLR-001", "Floor Cleaner 1L", 3, 3, "litre", 110, 150, 12, 2),
    ("CLN-GLV-001", "Rubber Gloves (Pair)", 3, 3, "pcs", 45, 75, 10, 1),
    ("CLN-MOP-001", "Spin Mop Refill", 3, 3, "pcs", 120, 180, 5, 0.6),
    ("CLN-GBG-001", "Garbage Bags (30 pcs)", 3, 3, "pack", 70, 99, 20, 3),
    ("PER-SOP-001", "Bath Soap 100g", 4, 2, "pcs", 32, 45, 30, 6),
    ("PER-SHM-001", "Shampoo 340ml", 4, 2, "pcs", 180, 245, 10, 2),
    ("PER-TPS-001", "Toothpaste 150g", 4, 2, "pcs", 75, 99, 20, 4),
    ("PER-TBR-001", "Toothbrush Medium", 4, 2, "pcs", 25, 40, 25, 3),
    ("PER-HSN-001", "Hand Sanitiser 500ml", 4, 3, "pcs", 120, 175, 10, 1),
    ("PER-TIS-001", "Facial Tissues (100 Pulls)", 4, 2, "pack", 55, 80, 15, 2),
    ("HRD-HAM-001", "Claw Hammer 500g", 5, 4, "pcs", 240, 350, 4, 0.3),
    ("HRD-SCR-001", "Screwdriver Set (6 pc)", 5, 4, "pack", 210, 320, 5, 0.4),
    ("HRD-NAI-001", "Wire Nails 2 inch (1kg)", 5, 4, "kg", 95, 140, 8, 1),
    ("HRD-TAP-001", "Insulation Tape", 5, 4, "pcs", 18, 30, 30, 4),
    ("HRD-DRL-001", "Drill Bit Set (10 pc)", 5, 4, "pack", 380, 560, 3, 0.3),
    ("HRD-PNT-001", "Wall Paint White 1L", 5, 4, "litre", 290, 399, 6, 1),
    ("HRD-FEV-001", "Wood Adhesive 200g", 5, 4, "pcs", 70, 105, 10, 1),
)

# Products whose reorders "get forgotten" late in the simulation.
NEGLECTED = {"STA-PEN-002", "ELE-BAT-001", "GRO-SUG-001", "CLN-GBG-001", "PER-SOP-001",
             "HRD-TAP-001"}


@dataclass
class SimProduct:
    """Simulation state for one product."""

    id: int
    sku: str
    rate: float
    reorder_level: int
    quantity: int
    pending: list[tuple[int, int]] = field(default_factory=list)  # (arrival day, qty)


@dataclass
class Stats:
    """Counters printed at the end."""

    ins: int = 0
    outs: int = 0
    adjustments: int = 0
    errors: int = 0


# -- master data -----------------------------------------------------------------
def create_master_data(services: AppServices, rng: random.Random) -> list[SimProduct]:
    """Create categories, suppliers and products; return simulation state."""
    category_ids = [services.categories.create(name, desc).id for name, desc in CATEGORIES]
    supplier_ids = [services.suppliers.create(data).id for data in SUPPLIERS]
    sims = []
    for sku, name, cat, sup, unit, cost, price, reorder, rate in PRODUCTS:
        product = services.products.create({
            "sku": sku, "name": name, "category_id": category_ids[cat],
            "supplier_id": supplier_ids[sup], "unit": unit, "unit_cost": cost,
            "selling_price": price, "reorder_level": reorder,
        }).product
        sims.append(SimProduct(product.id, sku, rate, reorder, 0))
    return sims


def record_sample_mistakes(services: AppServices) -> int:
    """Capture typical operator input errors (Poka-Yoke catches) as ERROR entries."""
    category_id = services.categories.list_all()[0].id
    attempts = [
        ("Products > Add", lambda: services.products.create(
            {"sku": "pen 001", "name": "Pen", "category_id": category_id, "unit": "pcs",
             "unit_cost": "5", "selling_price": "8", "reorder_level": "5"})),
        ("Products > Add", lambda: services.products.create(
            {"sku": "STA-PEN-001", "name": "Duplicate pen", "category_id": category_id,
             "unit": "pcs", "unit_cost": "5", "selling_price": "8", "reorder_level": "5"})),
        ("Suppliers > Add", lambda: services.suppliers.create(
            {"name": "Quick Supplies", "email": "orders@quick"})),
        ("Categories > Add", lambda: services.categories.create("stationery")),
        ("Products > Edit", lambda: services.products.create(
            {"sku": "GRO-NEW-001", "name": "Ghee 1L", "category_id": category_id,
             "unit": "litre", "unit_cost": "-560", "selling_price": "620",
             "reorder_level": "5"})),
    ]
    for context, attempt in attempts:
        try:
            attempt()
        except AppError as exc:
            services.activity.record_error(context, exc)
    return len(attempts)


# -- simulation ------------------------------------------------------------------
def at(day: date, hour: int, minute: int = 0) -> datetime:
    """Datetime on ``day`` at ``hour:minute``."""
    return datetime.combine(day, time(hour, minute))


def daily_demand(rng: random.Random, rate: float, day: date) -> int:
    """Random units demanded today (lower on Sundays)."""
    if day.weekday() == 6:
        rate *= 0.4
    if rate < 1:
        return 1 if rng.random() < rate else 0
    return max(0, round(rng.gauss(rate, rate * 0.5)))


def receive_orders(services: AppServices, sim: SimProduct, day_no: int, day: date,
                   stats: Stats) -> None:
    """Book purchase orders that arrive today."""
    for arrival, qty in [p for p in sim.pending if p[0] == day_no]:
        services.stock.stock_in(sim.id, qty, note=f"PO-{day:%y%m%d}-{sim.id:03d}",
                                occurred_at=at(day, 9, 15))
        sim.quantity += qty
        stats.ins += 1
    sim.pending = [p for p in sim.pending if p[0] != day_no]


def issue_demand(services: AppServices, sim: SimProduct, demand: int, day: date,
                 rng: random.Random, stats: Stats) -> None:
    """Issue today's demand; record a StockError when demand exceeds stock."""
    when = at(day, rng.randint(10, 19), rng.randint(0, 59))
    issue = demand
    if demand > sim.quantity:
        try:
            services.stock.stock_out(sim.id, demand, note="Counter sale", occurred_at=when)
        except StockError as exc:
            services.activity.record_error("Stock > Stock out", exc, entity="Product")
            stats.errors += 1
        issue = sim.quantity
    if issue > 0:
        services.stock.stock_out(sim.id, issue, note=f"Sale INV-{day:%y%m%d}",
                                 occurred_at=when)
        sim.quantity -= issue
        stats.outs += 1


def maybe_reorder(sim: SimProduct, day_no: int, rng: random.Random) -> None:
    """Place a purchase order when stock reaches the reorder level."""
    neglected = sim.sku in NEGLECTED and day_no >= NEGLECT_FROM_DAY
    if sim.quantity <= sim.reorder_level and not sim.pending and not neglected:
        quantity = math.ceil(sim.rate * rng.randint(18, 30)) + sim.reorder_level
        sim.pending.append((day_no + rng.randint(2, 5), quantity))


def maybe_adjust(services: AppServices, sim: SimProduct, day: date, rng: random.Random,
                 stats: Stats) -> None:
    """Weekly cycle count: occasionally a few units are damaged or missing."""
    if day.weekday() == 5 and sim.quantity > 3 and rng.random() < 0.06:
        counted = sim.quantity - rng.randint(1, 3)
        reason = rng.choice(("Cycle count: damaged packaging", "Cycle count: units missing",
                             "Expired stock written off"))
        services.stock.adjust(sim.id, counted, reason, occurred_at=at(day, 18, 30))
        sim.quantity = counted
        stats.adjustments += 1


def opening_stock(services: AppServices, sims: list[SimProduct], start: date,
                  rng: random.Random, stats: Stats) -> None:
    """Initial delivery for every product on the first day."""
    for sim in sims:
        qty = math.ceil(sim.rate * rng.randint(20, 32)) + sim.reorder_level
        services.stock.stock_in(sim.id, qty, note="Opening stock", occurred_at=at(start, 9))
        sim.quantity = qty
        stats.ins += 1


def simulate(services: AppServices, sims: list[SimProduct], rng: random.Random) -> Stats:
    """Run the day-by-day simulation ending today."""
    stats = Stats()
    start = date.today() - timedelta(days=SIMULATION_DAYS - 1)
    opening_stock(services, sims, start, rng, stats)
    for day_no in range(1, SIMULATION_DAYS):
        day = start + timedelta(days=day_no)
        if day.weekday() == 0:  # Monday shift change, audited as SETTINGS_CHANGE
            services.settings.save({"operator_name": OPERATORS[(day_no // 7) % len(OPERATORS)]})
        for sim in sims:
            receive_orders(services, sim, day_no, day, stats)
            demand = daily_demand(rng, sim.rate, day)
            if demand:
                issue_demand(services, sim, demand, day, rng, stats)
            maybe_adjust(services, sim, day, rng, stats)
            maybe_reorder(sim, day_no, rng)
    return stats


# -- entry point -----------------------------------------------------------------
def prepare_database(config: AppConfig, reset: bool) -> Database:
    """Open (optionally recreate) and migrate the configured database."""
    path = config.resolve_path("paths.database")
    if reset and path.exists():
        path.unlink()
    db = Database(path)
    db.initialize()
    return db


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, seed the database and print a summary.

    Returns:
        Process exit code (0 on success).
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="delete and recreate the database")
    parser.add_argument("--seed", type=int, default=240302054, help="random seed")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    config = load_config()
    setup_file_logging(config, level="ERROR")  # keep app.log quiet while bulk-seeding
    db = prepare_database(config, args.reset)
    services = build_services(config, db)
    if services.products.find(ListQuery()).total:
        print("Database already contains products. Use --reset to re-seed.")
        return 1
    rng = random.Random(args.seed)
    with db.transaction():  # one commit for the whole seed (fast, all-or-nothing)
        sims = create_master_data(services, rng)
        mistakes = record_sample_mistakes(services)
        stats = simulate(services, sims, rng)
        services.settings.save({"operator_name": config.get("operator.name")})
    print_summary(services, stats, mistakes, db.path)
    db.close()
    return 0


def print_summary(services: AppServices, stats: Stats, mistakes: int, db_path: str) -> None:
    """Print what was created."""
    dashboard = services.reports.dashboard_stats()
    symbol = services.settings.get("currency_symbol")
    print(f"Seeded {db_path}")
    print(f"  categories: {len(CATEGORIES)}, suppliers: {len(SUPPLIERS)}, "
          f"products: {len(PRODUCTS)}")
    print(f"  stock in: {stats.ins}, stock out: {stats.outs}, adjustments: {stats.adjustments}")
    print(f"  over-issue attempts logged: {stats.errors}, input mistakes logged: {mistakes}")
    print(f"  stock value: {symbol}{dashboard.total_stock_value:,.2f}, "
          f"low stock: {dashboard.low_stock_count}, stockouts: {dashboard.stockout_count}, "
          f"turnover ({dashboard.period_days} d): {dashboard.turnover:.2f}x")


if __name__ == "__main__":
    raise SystemExit(main())
