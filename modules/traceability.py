"""Batch traceability — trace any batch from raw material to customer."""
import pandas as pd
from modules.database import query, scalar


def trace_batch(batch_code):
    """Trace a batch through the full supply chain.

    Supports batch code formats:
    - Factory format: D6067K (Defrost), F6043A (Fresh)
    - Legacy format: RM-YYMMDD-NNNN (raw material), PR-YYMMDD-NNNN (production)
    """
    batch_code = batch_code.strip().upper()
    result = {"batch_code": batch_code, "found": False}

    # Try production batch first (F/D prefix or PR- prefix)
    prod = query(
        "SELECT p.*, pr.name as product_name, pr.product_type, pr.shelf_life_days "
        "FROM production p JOIN products pr ON p.product_id = pr.id "
        "WHERE UPPER(p.batch_code) = :b",
        {"b": batch_code}
    )

    if not prod.empty:
        result["found"] = True
        result["production"] = prod

        # Trace back to raw materials
        rm_batch = prod.iloc[0].get("raw_material_batch")
        if rm_batch:
            rm = query("SELECT * FROM raw_materials WHERE batch_code = :b", {"b": rm_batch})
            result["raw_materials"] = rm
        else:
            result["raw_materials"] = pd.DataFrame()

        # Trace forward to orders
        orders = query(
            "SELECT o.*, pr.name as product_name FROM orders o "
            "JOIN products pr ON o.product_id = pr.id "
            "WHERE o.production_batch = :b",
            {"b": batch_code}
        )
        result["orders"] = orders
        return result

    # Try raw material batch
    rm = query("SELECT * FROM raw_materials WHERE UPPER(batch_code) = :b", {"b": batch_code})
    if not rm.empty:
        result["found"] = True
        result["raw_materials"] = rm

        # Find production runs using this raw material
        prod = query(
            "SELECT p.*, pr.name as product_name FROM production p "
            "JOIN products pr ON p.product_id = pr.id "
            "WHERE p.raw_material_batch = :b",
            {"b": batch_code}
        )
        result["production"] = prod

        if not prod.empty:
            prod_batches = prod["batch_code"].tolist()
            placeholders = ",".join([f"'{b}'" for b in prod_batches])
            orders = query(
                f"SELECT o.*, pr.name as product_name FROM orders o "
                f"JOIN products pr ON o.product_id = pr.id "
                f"WHERE o.production_batch IN ({placeholders})"
            )
            result["orders"] = orders
        else:
            result["orders"] = pd.DataFrame()
        return result

    return result


def get_traceability_score():
    """Calculate % of production runs with complete traceability chain."""
    total = scalar("SELECT COUNT(*) FROM production")
    linked = scalar("SELECT COUNT(*) FROM production WHERE raw_material_batch IS NOT NULL")
    if total and total > 0:
        return round((linked / total) * 100, 1)
    return 0.0


def get_recent_batches(limit=20):
    """Get most recent production batches for quick lookup."""
    return query(f"""
        SELECT p.batch_code, p.date, pr.name as product_name,
               p.finished_output_kg, p.yield_pct, p.raw_material_batch
        FROM production p
        JOIN products pr ON p.product_id = pr.id
        ORDER BY p.date DESC, p.id DESC
        LIMIT {limit}
    """)
