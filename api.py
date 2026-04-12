"""FastAPI REST API for compliance analytics.

Run: uvicorn api:app --reload
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DB_PATH = Path("data/factory_compliance.db")

app = FastAPI(
    title="Manufacturing Compliance API",
    description="REST API for BRC/HACCP food safety compliance data",
    version="1.0.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

class HealthCheck(BaseModel):
    status: str
    db_connected: bool
    timestamp: str

@app.get("/health", response_model=HealthCheck)
def health_check():
    try:
        with get_db() as conn:
            conn.execute("SELECT 1")
            db_ok = True
    except Exception:
        db_ok = False
    return HealthCheck(status="healthy" if db_ok else "degraded", db_connected=db_ok, timestamp=datetime.utcnow().isoformat())

@app.get("/batches")
def get_batches(status: Optional[str] = None, limit: int = Query(100, le=1000)):
    with get_db() as conn:
        query = "SELECT batch_code, product_id, production_date, yield_pct, status, alert_flag FROM batches"
        params = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY production_date DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in conn.execute(query, params).fetchall()]

@app.get("/batches/{batch_code}")
def get_batch(batch_code: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM batches WHERE batch_code = ?", (batch_code,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Batch {batch_code} not found")
    return dict(row)

@app.get("/temperature")
def get_temperature_logs(location: Optional[str] = None, excursions_only: bool = False, limit: int = Query(100, le=5000)):
    with get_db() as conn:
        query = "SELECT location, temperature, timestamp, is_excursion FROM temperature_logs WHERE 1=1"
        params = []
        if location:
            query += " AND location = ?"
            params.append(location)
        if excursions_only:
            query += " AND is_excursion = 1"
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in conn.execute(query, params).fetchall()]

@app.get("/shelf-life/risk")
def get_shelf_life_risk(risk_level: Optional[str] = None):
    with get_db() as conn:
        base = """SELECT batch_code, age_days, life_days, (life_days - age_days) as remaining_days,
            CASE WHEN (life_days - age_days) <= 0 THEN 'EXPIRED'
                 WHEN (life_days - age_days) <= 2 THEN 'CRITICAL'
                 WHEN (life_days - age_days) <= 5 THEN 'WARNING'
                 ELSE 'OK' END as risk_level
            FROM batches WHERE life_days > 0"""
        if risk_level:
            query = f"SELECT * FROM ({base}) sub WHERE risk_level = ? ORDER BY remaining_days"
            return [dict(r) for r in conn.execute(query, (risk_level,)).fetchall()]
        query = f"SELECT * FROM ({base}) sub WHERE risk_level != 'OK' ORDER BY remaining_days"
        return [dict(r) for r in conn.execute(query).fetchall()]

@app.get("/yield/summary")
def get_yield_summary():
    with get_db() as conn:
        return [dict(r) for r in conn.execute("""
            SELECT shift, line_number, COUNT(*) as batch_count,
                   ROUND(AVG(yield_pct), 2) as avg_yield_pct,
                   ROUND(SUM(waste_kg), 2) as total_waste_kg
            FROM batches WHERE raw_input_kg > 0
            GROUP BY shift, line_number ORDER BY shift, line_number
        """).fetchall()]
