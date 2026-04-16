"""Shared pytest fixtures for the compliance dashboard test suite.

Tests avoid hitting the real SQLite file on disk. Instead they build an
in-memory SQLite schema tailored to the specific query being exercised
and monkeypatch the ``modules.database`` helpers so production code
paths remain untouched.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

# Make the project importable when pytest is invoked from the repo root.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


@pytest.fixture
def sqlite_memory():
    """Yield a fresh in-memory SQLite connection with synthetic tables."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            code TEXT,
            name TEXT,
            product_type TEXT,
            shelf_life_days INTEGER,
            allergens TEXT
        );

        CREATE TABLE production (
            id INTEGER PRIMARY KEY,
            batch_code TEXT,
            product_id INTEGER,
            date TEXT,
            pack_date TEXT,
            use_by_date TEXT,
            raw_material_batch TEXT,
            finished_output_kg REAL,
            yield_pct REAL,
            concession_required INTEGER DEFAULT 0,
            concession_reason TEXT
        );

        CREATE TABLE raw_materials (
            id INTEGER PRIMARY KEY,
            batch_code TEXT,
            supplier TEXT,
            intake_date TEXT
        );

        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer TEXT,
            product_id INTEGER,
            production_batch TEXT,
            quantity_kg REAL,
            order_date TEXT
        );

        CREATE TABLE concessions (
            id INTEGER PRIMARY KEY,
            batch_code TEXT,
            product_id INTEGER,
            reason TEXT,
            pack_date TEXT,
            original_use_by TEXT,
            extended_use_by TEXT,
            approved_by TEXT,
            approved_date TEXT,
            status TEXT
        );

        CREATE TABLE temp_logs (
            id INTEGER PRIMARY KEY,
            location TEXT,
            temperature REAL,
            recorded_at TEXT,
            recorded_by TEXT
        );
        """
    )

    today = datetime.now(timezone.utc).date()
    conn.executemany(
        "INSERT INTO products (id, code, name, product_type, shelf_life_days, allergens) VALUES (?, ?, ?, ?, ?, ?)",
        [
            (1, "SKU-100", "Synthetic Fillet", "Fresh", 9, "Fish"),
            (2, "SKU-200", "Synthetic Portion", "Defrost", 11, "Fish;Sulphites"),
        ],
    )
    conn.executemany(
        "INSERT INTO production (batch_code, product_id, date, pack_date, use_by_date, raw_material_batch, finished_output_kg, yield_pct, concession_required) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("F0001A", 1, str(today - timedelta(days=2)), str(today - timedelta(days=2)),
             str(today + timedelta(days=7)), "RM-001", 420.0, 88.0, 0),
            ("F0002A", 1, str(today - timedelta(days=1)), str(today - timedelta(days=1)),
             str(today + timedelta(days=2)), "RM-002", 380.0, 85.0, 0),
            ("D0003A", 2, str(today - timedelta(days=5)), str(today - timedelta(days=5)),
             str(today + timedelta(days=1)), None, 260.0, 79.0, 1),
        ],
    )
    conn.executemany(
        "INSERT INTO raw_materials (batch_code, supplier, intake_date) VALUES (?, ?, ?)",
        [
            ("RM-001", "Synthetic Supplier Ltd", str(today - timedelta(days=4))),
            ("RM-002", "Synthetic Supplier Ltd", str(today - timedelta(days=3))),
        ],
    )
    conn.executemany(
        "INSERT INTO orders (customer, product_id, production_batch, quantity_kg, order_date) VALUES (?, ?, ?, ?, ?)",
        [
            ("Customer Alpha", 1, "F0001A", 200.0, str(today - timedelta(days=1))),
            ("Customer Beta", 2, "D0003A", 150.0, str(today)),
        ],
    )
    conn.executemany(
        "INSERT INTO temp_logs (location, temperature, recorded_at, recorded_by) VALUES (?, ?, ?, ?)",
        [
            ("Zone A", 0.0, str(today), "probe-a"),
            ("Zone A", 3.5, str(today), "probe-a"),   # excursion above +1 max
            ("Zone B", 2.0, str(today), "probe-b"),
            ("Zone D", -19.0, str(today), "probe-d"),
            ("Zone D", -10.0, str(today), "probe-d"),  # excursion above -18 max
        ],
    )
    conn.commit()
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def patched_db(monkeypatch, sqlite_memory):
    """Redirect modules.database.query/scalar to the in-memory connection."""
    from modules import database

    def _fake_query(sql, params=None):
        if params:
            cur = sqlite_memory.execute(sql, params)
        else:
            cur = sqlite_memory.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        return pd.DataFrame(rows, columns=cols)

    def _fake_scalar(sql, params=None):
        df = _fake_query(sql, params)
        if df.empty:
            return None
        return df.iloc[0, 0]

    monkeypatch.setattr(database, "query", _fake_query)
    monkeypatch.setattr(database, "scalar", _fake_scalar)
    # Also patch any modules that imported query/scalar directly.
    for module_name in (
        "modules.temperature",
        "modules.traceability",
        "modules.shelf_life",
        "modules.allergens",
        "modules.slo",
    ):
        if module_name in sys.modules:
            mod = sys.modules[module_name]
            if hasattr(mod, "query"):
                monkeypatch.setattr(mod, "query", _fake_query, raising=False)
            if hasattr(mod, "scalar"):
                monkeypatch.setattr(mod, "scalar", _fake_scalar, raising=False)
    return sqlite_memory


@pytest.fixture
def sop_dir(tmp_path: Path) -> Path:
    """Create a small synthetic SOP directory for RAG tests."""
    (tmp_path / "sop_one.md").write_text(
        "# Temperature Monitoring\n\nChilled storage must remain between 0 and 4 degC.\n"
        "Excursions above 4 degC for longer than fifteen minutes require\n"
        "investigation and corrective action.\n",
        encoding="utf-8",
    )
    (tmp_path / "sop_two.md").write_text(
        "# Traceability\n\nEvery production batch must record the raw material\n"
        "batch, supplier lot reference and intake date so recall can be\n"
        "completed within four hours.\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("placeholder - should be skipped\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def isolated_config_dir(tmp_path: Path, monkeypatch) -> Path:
    """Point module loaders at an isolated copy of config.yaml."""
    src = _PROJECT_ROOT / "config.yaml"
    dst = tmp_path / "config.yaml"
    if src.exists():
        dst.write_bytes(src.read_bytes())
    monkeypatch.setenv("COMPLIANCE_CONFIG", str(dst))
    return tmp_path
