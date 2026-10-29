"""Tests for validators, formatters, date helpers and CSV export.

Layer: tests
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from config.config_loader import AppConfig
from core.exceptions import ValidationError
from utils.csv_export import default_export_path, write_csv
from utils.date_helpers import date_range, days_ago, days_between, period_bounds
from utils.formatters import (
    format_currency,
    format_date,
    format_datetime,
    format_days,
    format_ratio,
    truncate,
)
from utils.validators import Validator, is_valid_strftime


@pytest.fixture()
def validator(config: AppConfig) -> Validator:
    """Validator using shipped config limits."""
    return Validator(config)


# -- validators -----------------------------------------------------------------
def test_text_required_and_trimmed(validator: Validator) -> None:
    """Blank required text is refused; whitespace is trimmed."""
    assert validator.text("  Pen ", "Name") == "Pen"
    with pytest.raises(ValidationError, match="Name is required"):
        validator.text("   ", "Name")


def test_text_max_length(validator: Validator) -> None:
    """Text longer than the configured limit is refused."""
    with pytest.raises(ValidationError, match="at most"):
        validator.text("x" * (validator.text_max + 1), "Name")


@pytest.mark.parametrize("raw", ["abc", "1.5", ""])
def test_integer_rejects_non_whole_numbers(validator: Validator, raw: str) -> None:
    """Letters, decimals and blanks are not whole numbers."""
    with pytest.raises(ValidationError):
        validator.integer(raw, "Quantity", minimum=1)


def test_integer_bounds(validator: Validator) -> None:
    """Minimum and maximum are enforced."""
    assert validator.integer(" 5 ", "Qty", minimum=1, maximum=10) == 5
    with pytest.raises(ValidationError, match="at least 1"):
        validator.integer("0", "Qty", minimum=1)
    with pytest.raises(ValidationError, match="at most 10"):
        validator.integer("11", "Qty", maximum=10)


def test_decimal_non_negative_and_rounded(validator: Validator) -> None:
    """Negative prices and NaN are refused; values round to cents."""
    assert validator.decimal("12.345", "Cost") == 12.35
    for bad in ("-1", "nan", "ten"):
        with pytest.raises(ValidationError):
            validator.decimal(bad, "Cost")


def test_sku_format(validator: Validator) -> None:
    """SKUs are upper-cased and must match the pattern."""
    assert validator.sku("sta-pen-001") == "STA-PEN-001"
    with pytest.raises(ValidationError, match="SKU"):
        validator.sku("has space")


def test_email_and_phone(validator: Validator) -> None:
    """Optional contact fields accept blanks but reject bad formats."""
    assert validator.email("") == "" and validator.phone("") == ""
    assert validator.email("a@b.in") == "a@b.in"
    assert validator.phone("+91 98765-43210") == "+91 98765-43210"
    with pytest.raises(ValidationError, match="Email"):
        validator.email("not-an-email")
    with pytest.raises(ValidationError, match="Phone"):
        validator.phone("12ab")


def test_choice_and_date(validator: Validator) -> None:
    """Choices are enforced; dates parse in the configured format."""
    assert validator.choice("IN", "Type", ["IN", "OUT"]) == "IN"
    with pytest.raises(ValidationError):
        validator.choice("SIDEWAYS", "Type", ["IN", "OUT"])
    assert validator.date("31/12/2026", "From", "%d/%m/%Y") == date(2026, 12, 31)
    assert validator.date("", "From", "%d/%m/%Y") is None
    with pytest.raises(ValidationError, match="date like"):
        validator.date("2026-12-31", "From", "%d/%m/%Y")


def test_is_valid_strftime() -> None:
    """Only round-trippable date formats are accepted."""
    assert is_valid_strftime("%d-%m-%Y")
    assert not is_valid_strftime("dd-mm-yyyy")
    assert not is_valid_strftime("%H:%M")


# -- formatters -----------------------------------------------------------------
def test_formatters() -> None:
    """Money, dates, ratios and durations render consistently."""
    assert format_currency(1234.5, "₹") == "₹1,234.50"
    assert format_currency(-3, "$") == "-$3.00"
    assert format_date("2026-10-30 14:05:00", "%d/%m/%Y") == "30/10/2026"
    assert format_datetime("2026-10-30 14:05:00", "%Y-%m-%d") == "2026-10-30 14:05"
    assert format_date("garbage", "%Y") == "garbage"
    assert format_ratio(2.345) == "2.35x"
    assert format_days(None) == "No usage" and format_days(3) == "3.0 days"
    assert truncate("abcdef", 4) == "abc…" and truncate("ab", 4) == "ab"


# -- dates ----------------------------------------------------------------------
def test_date_helpers() -> None:
    """Period bounds cover whole days inclusively."""
    start, end = date(2026, 1, 1), date(2026, 1, 3)
    assert period_bounds(start, end) == ("2026-01-01 00:00:00", "2026-01-03 23:59:59")
    assert days_between(start, end) == 3 and len(date_range(start, end)) == 3
    assert days_ago(1, date(2026, 1, 1)) == date(2025, 12, 31)


# -- csv ------------------------------------------------------------------------
def test_write_csv(tmp_path: Path) -> None:
    """Columns are selected, renamed and written with a BOM."""
    path = write_csv([{"sku": "A1", "name": "Pen", "secret": 1}],
                     [("sku", "SKU"), ("name", "Name")], tmp_path / "out" / "p.csv")
    frame = pd.read_csv(path, encoding="utf-8-sig")
    assert list(frame.columns) == ["SKU", "Name"] and frame.iloc[0]["Name"] == "Pen"
    assert default_export_path(tmp_path, "products").name.startswith("products_")
