"""Natural language query interface for compliance auditors.

Translates plain-English questions into structured calls to existing modules.
Uses pattern matching (regex), NOT an LLM — works offline with zero dependencies.

Inspired by PyCon DE 2026: "From Ticket to Draft" (Munich AI, Lukas).
"""
from __future__ import annotations

import re
from typing import Any

from modules import allergens, shelf_life, temperature, traceability

_BATCH_CODE = re.compile(r"[DF]\d{4}[A-Z]", re.IGNORECASE)
_DAYS = re.compile(r"(\d+)\s*days?", re.IGNORECASE)

EXAMPLE_QUERIES = [
    "Show temperature excursions in the last 7 days",
    "Trace batch D6067K",
    "Which batches expire in 3 days?",
    "Show allergen matrix",
    "What is the compliance score?",
    "List concessions from the last 30 days",
]


def _extract_days(text: str, default: int = 7) -> int:
    m = _DAYS.search(text)
    return int(m.group(1)) if m else default


def _extract_batch(text: str) -> str | None:
    m = _BATCH_CODE.search(text)
    return m.group(0).upper() if m else None


def parse_query(text: str) -> dict[str, Any]:
    """Parse a natural language query and return structured results."""
    if not text or not text.strip():
        return {"intent": "unknown", "suggestions": EXAMPLE_QUERIES}

    lower = text.lower().strip()

    # Temperature excursions
    if any(kw in lower for kw in ("temperature", "excursion", "temp ", "cold")):
        days = _extract_days(text)
        try:
            result = temperature.get_excursions(days=days)
            return {"intent": "temperature_excursions", "params": {"days": days}, "result": result}
        except Exception as e:
            return {"intent": "temperature_excursions", "params": {"days": days}, "error": str(e)}

    # Batch traceability
    batch = _extract_batch(text)
    if batch or "trace" in lower:
        if not batch:
            return {"intent": "trace_batch", "error": "No batch code found. Use format D6067K or F6043A."}
        try:
            result = traceability.trace_batch(batch)
            return {"intent": "trace_batch", "params": {"batch_code": batch}, "result": result}
        except Exception as e:
            return {"intent": "trace_batch", "params": {"batch_code": batch}, "error": str(e)}

    # Expiring batches
    if any(kw in lower for kw in ("expir", "use by", "use-by", "shelf life")):
        days = _extract_days(text, default=3)
        try:
            result = shelf_life.get_expiring_soon(days=days)
            return {"intent": "expiring_soon", "params": {"days": days}, "result": result}
        except Exception as e:
            return {"intent": "expiring_soon", "params": {"days": days}, "error": str(e)}

    # Allergens
    if "allergen" in lower:
        try:
            result = allergens.get_allergen_matrix()
            return {"intent": "allergen_matrix", "result": result}
        except Exception as e:
            return {"intent": "allergen_matrix", "error": str(e)}

    # Compliance score
    if any(kw in lower for kw in ("compliance", "score", "audit")):
        try:
            temp_score = temperature.get_compliance_score()
            trace_score = traceability.get_traceability_score()
            return {
                "intent": "compliance_score",
                "result": {
                    "temperature": temp_score,
                    "traceability": trace_score,
                    "overall": round((temp_score + trace_score) / 2, 1),
                },
            }
        except Exception as e:
            return {"intent": "compliance_score", "error": str(e)}

    # Concessions
    if "concession" in lower:
        days = _extract_days(text, default=30)
        try:
            result = shelf_life.get_concessions(days=days)
            return {"intent": "concessions", "params": {"days": days}, "result": result}
        except Exception as e:
            return {"intent": "concessions", "params": {"days": days}, "error": str(e)}

    return {"intent": "unknown", "suggestions": EXAMPLE_QUERIES}


def get_query_context() -> str:
    """Return a system prompt describing available data for LLM integration."""
    return """You are a BRC/HACCP compliance assistant for a fish processing factory.

Available data:
- Temperature logs: readings from 6 zones (Superchill, Chiller 1/2, Freezer, Production Floor, Dispatch Bay)
- Batch traceability: raw materials -> production -> customer orders
- Allergen matrix: 14 EU allergens tracked per product
- Shelf life: use-by dates, concessions, FEFO despatch priority
- Compliance scoring: temperature compliance (target 95%), traceability (target 90%)

Answer questions using specific data. Reference batch codes (format: D6067K or F6043A),
temperature zones, and allergen names. Use GBP for costs and kg for weights."""
