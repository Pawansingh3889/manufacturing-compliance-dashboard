"""MCP server exposing BRC/HACCP compliance data as tools.

Allows LLM agents to query compliance status, trace batches,
check allergens, and monitor temperature excursions.

Run: python mcp_server.py
"""
from __future__ import annotations

import json
import logging
import os

from fastmcp import FastMCP

from modules import allergens, shelf_life, temperature, traceability
from modules.database import load_config

log = logging.getLogger(__name__)

mcp = FastMCP(
    "Compliance Dashboard MCP",
    description=(
        "BRC/HACCP food safety compliance tools for fish manufacturing. "
        "Provides batch traceability, temperature monitoring, allergen matrix, "
        "and compliance scoring."
    ),
)


@mcp.tool()
def trace_batch(batch_code: str) -> str:
    """Trace a production batch from raw materials to customer orders.

    Returns the full supply chain for a batch: raw material intake,
    production run details (yield, waste, dates), and customer orders.

    Args:
        batch_code: Batch identifier (format: D6067K or F6043A).
    """
    try:
        result = traceability.trace_batch(batch_code)
        serializable = {}
        for key, val in result.items():
            if hasattr(val, "to_dict"):
                serializable[key] = val.to_dict(orient="records")
            else:
                serializable[key] = val
        return json.dumps(serializable, default=str)
    except Exception as exc:
        log.exception("trace_batch failed for %s", batch_code)
        return json.dumps({"error": str(exc)})


@mcp.tool()
def get_temperature_excursions(days: int = 7) -> str:
    """Get temperature readings that exceeded safe limits.

    Returns excursions from all 6 monitored zones over the specified
    period, with severity flags.

    Args:
        days: Number of days to look back (default 7).
    """
    try:
        df = temperature.get_excursions(days=days)
        return df.to_json(orient="records", date_format="iso")
    except Exception as exc:
        log.exception("get_temperature_excursions failed")
        return json.dumps({"error": str(exc)})


@mcp.tool()
def get_allergen_matrix() -> str:
    """Get the product-by-allergen cross-reference matrix.

    Returns all products with their allergen flags for 14 EU allergens.
    """
    try:
        df = allergens.get_allergen_matrix()
        return df.to_json(orient="records")
    except Exception as exc:
        log.exception("get_allergen_matrix failed")
        return json.dumps({"error": str(exc)})


@mcp.tool()
def get_compliance_score() -> str:
    """Get the current BRC compliance score.

    Returns temperature compliance, traceability compliance,
    and the weighted overall score.
    """
    try:
        config = load_config()
        weights = config.get("scoring", {})
        temp_weight = weights.get("temperature_weight", 0.4)
        trace_weight = weights.get("traceability_weight", 0.4)

        temp_score = temperature.get_compliance_score()
        trace_score = traceability.get_traceability_score()
        overall = round(temp_score * temp_weight + trace_score * trace_weight, 1)

        return json.dumps({
            "temperature_score": temp_score,
            "traceability_score": trace_score,
            "overall_score": overall,
            "passing_threshold": weights.get("passing_threshold", 85),
            "status": "PASS" if overall >= weights.get("passing_threshold", 85) else "FAIL",
        })
    except Exception as exc:
        log.exception("get_compliance_score failed")
        return json.dumps({"error": str(exc)})


@mcp.tool()
def get_expiring_batches(days: int = 3) -> str:
    """Get batches expiring within the specified number of days.

    Used for FEFO (First Expired, First Out) despatch planning.

    Args:
        days: Number of days to look ahead (default 3).
    """
    try:
        df = shelf_life.get_expiring_soon(days=days)
        return df.to_json(orient="records", date_format="iso")
    except Exception as exc:
        log.exception("get_expiring_batches failed")
        return json.dumps({"error": str(exc)})


@mcp.resource("health://status")
def health_status() -> str:
    """Server health and database connectivity."""
    try:
        from modules.database import scalar
        scalar("SELECT 1")
        return json.dumps({"status": "healthy", "server": "Compliance MCP"})
    except Exception as exc:
        return json.dumps({"status": f"degraded: {exc}", "server": "Compliance MCP"})


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    port = int(os.getenv("MCP_PORT", "9000"))
    log.info("Starting Compliance MCP server on port %s", port)
    mcp.run(transport="sse", host="localhost", port=port)


if __name__ == "__main__":
    main()
