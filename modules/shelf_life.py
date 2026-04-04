"""Shelf life tracking and concession management.

Fresh products: +19 days from pack date (superchill storage)
Defrost products: +11 days from pack date (chiller storage)
Beyond shelf life: concession required from Quality Manager
"""
import pandas as pd
from datetime import datetime, timedelta
from modules.database import query, scalar


def get_expiring_soon(days_ahead=3):
    """Find production batches expiring within N days."""
    return query(
        "SELECT p.batch_code, p.pack_date, p.use_by_date, "
        "pr.name as product_name, pr.product_type, pr.shelf_life_days, "
        "p.finished_output_kg, "
        "CAST(julianday(p.use_by_date) - julianday('now') AS INTEGER) as days_remaining, "
        "p.concession_required "
        "FROM production p "
        "JOIN products pr ON p.product_id = pr.id "
        "WHERE p.use_by_date >= date('now') "
        "AND p.use_by_date <= date('now', :ahead) "
        "ORDER BY p.use_by_date ASC",
        {"ahead": f"+{days_ahead} days"}
    )


def get_expired():
    """Find production batches that have passed their use-by date."""
    return query("""
        SELECT p.batch_code, p.pack_date, p.use_by_date,
               pr.name as product_name, pr.product_type,
               CAST(julianday('now') - julianday(p.use_by_date) AS INTEGER) as days_overdue,
               p.concession_required, p.concession_reason
        FROM production p
        JOIN products pr ON p.product_id = pr.id
        WHERE p.use_by_date < date('now')
        AND p.date >= date('now', '-14 days')
        ORDER BY p.use_by_date DESC
    """)


def get_concessions(days=30):
    """Get all concession records for the period."""
    return query(
        "SELECT c.batch_code, c.reason, c.pack_date, "
        "c.original_use_by, c.extended_use_by, "
        "c.approved_by, c.approved_date, c.status, "
        "pr.name as product_name "
        "FROM concessions c "
        "JOIN products pr ON c.product_id = pr.id "
        "WHERE c.approved_date >= date('now', :days_ago) "
        "ORDER BY c.approved_date DESC",
        {"days_ago": f"-{days} days"}
    )


def get_shelf_life_summary():
    """Get summary of shelf life compliance."""
    total_batches = scalar(
        "SELECT COUNT(*) FROM production WHERE date >= date('now', '-30 days')"
    ) or 0

    concession_batches = scalar(
        "SELECT COUNT(*) FROM production "
        "WHERE date >= date('now', '-30 days') AND concession_required = 1"
    ) or 0

    within_spec = total_batches - concession_batches

    return {
        "total_batches": int(total_batches),
        "within_spec": int(within_spec),
        "concessions": int(concession_batches),
        "compliance_pct": round((within_spec / total_batches) * 100, 1) if total_batches > 0 else 100.0,
    }


def decode_batch_code(batch_code):
    """Decode a factory batch code into its components.

    Format: D6067K or F6043A
    - D = Defrost, F = Fresh
    - 6 = year (2026)
    - 067 = day of year (Julian day)
    - K = sub-batch identifier
    """
    batch_code = batch_code.strip().upper()

    if len(batch_code) < 5:
        return None

    prefix = batch_code[0]
    if prefix not in ("D", "F"):
        return None

    product_type = "Defrost" if prefix == "D" else "Fresh"

    try:
        year_digit = int(batch_code[1])
        year = 2020 + year_digit
        julian = int(batch_code[2:5])
        sub_batch = batch_code[5:] if len(batch_code) > 5 else ""

        pack_date = datetime(year, 1, 1) + timedelta(days=julian - 1)
        shelf_days = 11 if prefix == "D" else 19
        use_by = pack_date + timedelta(days=shelf_days)

        return {
            "batch_code": batch_code,
            "product_type": product_type,
            "year": year,
            "julian_day": julian,
            "sub_batch": sub_batch,
            "pack_date": pack_date.strftime("%Y-%m-%d"),
            "use_by_date": use_by.strftime("%Y-%m-%d"),
            "shelf_life_days": shelf_days,
            "storage": "Superchill" if prefix == "F" else "Chiller",
        }
    except (ValueError, OverflowError):
        return None
