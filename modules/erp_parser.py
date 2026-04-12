"""ERP Data Parser — imports data from any food manufacturing ERP system.

Supports:
- SI Integreater (Aptean) exports via SSRS (SQL Server Reporting Services)
- Generic BRC-compliant CSV/Excel exports
- Custom column mapping via config

The parser auto-detects SSRS formatting (header rows, merged cells, footers)
and strips it before mapping columns to the dashboard schema.
"""
import re

import pandas as pd

from modules.ssrs_parser import parse_ssrs_file

# Standard column name mappings — maps common ERP export headers to our schema
# Left side: what ERPs typically call it (case-insensitive, partial match)
# Right side: what our database expects
COLUMN_MAPS = {
    # === RAW MATERIALS ===
    "raw_materials": {
        "batch": "batch_code",
        "batch_code": "batch_code",
        "batch code": "batch_code",
        "lot": "batch_code",
        "lot_code": "batch_code",
        "lot number": "batch_code",
        "intake_batch": "batch_code",
        "supplier": "supplier",
        "supplier_name": "supplier",
        "vendor": "supplier",
        "quantity": "quantity_kg",
        "qty": "quantity_kg",
        "weight": "quantity_kg",
        "net_weight": "quantity_kg",
        "quantity_kg": "quantity_kg",
        "received": "received_date",
        "received_date": "received_date",
        "intake_date": "received_date",
        "delivery_date": "received_date",
        "date": "received_date",
        "expiry": "expiry_date",
        "expiry_date": "expiry_date",
        "use_by": "expiry_date",
        "use_by_date": "expiry_date",
        "best_before": "expiry_date",
        "temp": "temperature_on_arrival",
        "temperature": "temperature_on_arrival",
        "arrival_temp": "temperature_on_arrival",
        "intake_temp": "temperature_on_arrival",
        "product": "product_name",
        "product_name": "product_name",
        "item": "product_name",
        "description": "product_name",
        "item_description": "product_name",
    },

    # === PRODUCTION ===
    "production": {
        "batch": "batch_code",
        "batch_code": "batch_code",
        "production_batch": "batch_code",
        "lot": "batch_code",
        "date": "date",
        "production_date": "date",
        "pack_date": "pack_date",
        "packed": "pack_date",
        "use_by": "use_by_date",
        "use_by_date": "use_by_date",
        "expiry": "use_by_date",
        "best_before": "use_by_date",
        "input": "raw_input_kg",
        "raw_input": "raw_input_kg",
        "input_kg": "raw_input_kg",
        "raw_weight": "raw_input_kg",
        "output": "finished_output_kg",
        "finished_output": "finished_output_kg",
        "output_kg": "finished_output_kg",
        "net_weight": "finished_output_kg",
        "packed_weight": "finished_output_kg",
        "waste": "waste_kg",
        "waste_kg": "waste_kg",
        "giveaway": "waste_kg",
        "yield": "yield_pct",
        "yield_pct": "yield_pct",
        "yield_%": "yield_pct",
        "line": "line_number",
        "line_number": "line_number",
        "production_line": "line_number",
        "shift": "shift",
        "operator": "operator",
        "operative": "operator",
        "team_leader": "operator",
        "product": "product_name",
        "product_name": "product_name",
        "item": "product_name",
        "description": "product_name",
        "rm_batch": "raw_material_batch",
        "raw_material_batch": "raw_material_batch",
        "intake_batch": "raw_material_batch",
        "source_batch": "raw_material_batch",
    },

    # === TEMPERATURE LOGS ===
    "temperature": {
        "location": "location",
        "zone": "location",
        "area": "location",
        "room": "location",
        "storage": "location",
        "temperature": "temperature",
        "temp": "temperature",
        "reading": "temperature",
        "value": "temperature",
        "recorded_at": "recorded_at",
        "timestamp": "recorded_at",
        "date_time": "recorded_at",
        "datetime": "recorded_at",
        "time": "recorded_at",
        "date": "recorded_at",
        "recorded_by": "recorded_by",
        "operator": "recorded_by",
        "checked_by": "recorded_by",
        "user": "recorded_by",
    },
}


def auto_map_columns(df, data_type):
    """Automatically map DataFrame columns to our schema using fuzzy matching.

    Args:
        df: pandas DataFrame with ERP export data
        data_type: one of 'raw_materials', 'production', 'temperature'

    Returns:
        tuple: (mapped_df, mapping_report)
    """
    if data_type not in COLUMN_MAPS:
        return df, {"error": f"Unknown data type: {data_type}"}

    col_map = COLUMN_MAPS[data_type]
    mapping = {}
    unmapped = []

    for col in df.columns:
        clean = col.strip().lower().replace(" ", "_").replace("-", "_")

        # Exact match
        if clean in col_map:
            mapping[col] = col_map[clean]
            continue

        # Partial match — check if any key is contained in the column name
        matched = False
        for key, target in col_map.items():
            if key in clean or clean in key:
                if target not in mapping.values():
                    mapping[col] = target
                    matched = True
                    break

        if not matched:
            unmapped.append(col)

    # Rename mapped columns
    mapped_df = df.rename(columns=mapping)

    report = {
        "mapped": mapping,
        "unmapped": unmapped,
        "total_columns": len(df.columns),
        "mapped_count": len(mapping),
        "unmapped_count": len(unmapped),
    }

    return mapped_df, report


def parse_erp_file(uploaded_file, data_type):
    """Parse an uploaded ERP export file and map to dashboard schema.

    Auto-detects SSRS formatting (SI Integreater exports) and strips
    header rows, merged cells, and footer totals before mapping columns.

    Args:
        uploaded_file: Streamlit UploadedFile object
        data_type: 'raw_materials', 'production', or 'temperature'

    Returns:
        tuple: (DataFrame, report_dict)
    """
    filename = uploaded_file.name.lower()

    # Step 1: Try SSRS parser first (handles SI Integreater exports)
    try:
        uploaded_file.seek(0)
        ssrs_df, ssrs_meta = parse_ssrs_file(uploaded_file)
        if ssrs_meta.get("is_ssrs") and not ssrs_df.empty:
            # SSRS format detected — use cleaned data
            mapped_df, report = auto_map_columns(ssrs_df, data_type)
            report["format"] = "SSRS (SI Integreater)"
            report["ssrs_metadata"] = ssrs_meta
            report["rows"] = len(mapped_df)
            report["source"] = filename
            return _post_process(mapped_df, report)
    except Exception:
        pass  # Fall through to standard parser

    # Step 2: Standard parser (non-SSRS files)
    uploaded_file.seek(0)

    try:
        if filename.endswith(".csv"):
            # Try different encodings and delimiters
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                for sep in [",", ";", "\t", "|"]:
                    try:
                        uploaded_file.seek(0)
                        df = pd.read_csv(uploaded_file, encoding=encoding, sep=sep)
                        if len(df.columns) > 1:
                            break
                    except Exception:
                        continue
                if len(df.columns) > 1:
                    break
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(uploaded_file)
        else:
            return None, {"error": f"Unsupported file: {filename}. Use CSV or Excel."}
    except Exception as e:
        return None, {"error": f"Failed to read file: {str(e)}"}

    if df.empty:
        return None, {"error": "File is empty."}

    # Clean column names
    df.columns = [str(c).strip() for c in df.columns]

    # Remove completely empty rows
    df = df.dropna(how="all")

    # Auto-map columns
    mapped_df, report = auto_map_columns(df, data_type)
    report["rows"] = len(mapped_df)
    report["source"] = filename
    report["format"] = "Standard CSV/Excel"

    return _post_process(mapped_df, report)


def _post_process(mapped_df, report):
    """Clean up dates, numbers, and formats after column mapping."""
    # Format dates
    date_cols = [c for c in mapped_df.columns if "date" in c.lower() or c in ("recorded_at", "pack_date")]
    for col in date_cols:
        if col in mapped_df.columns:
            mapped_df[col] = pd.to_datetime(mapped_df[col], errors="coerce", dayfirst=True)
            mapped_df[col] = mapped_df[col].dt.strftime("%Y-%m-%d")

    # Format temperatures
    if "temperature" in mapped_df.columns:
        mapped_df["temperature"] = pd.to_numeric(mapped_df["temperature"], errors="coerce")

    # Format weights
    for col in ["quantity_kg", "raw_input_kg", "finished_output_kg", "waste_kg"]:
        if col in mapped_df.columns:
            mapped_df[col] = pd.to_numeric(mapped_df[col], errors="coerce")

    return mapped_df, report


def detect_batch_format(batch_code):
    """Detect the batch code format from a sample.

    Returns the format type: 'si_factory' (D6067K), 'standard' (RM-YYMMDD-NNNN), or 'unknown'
    """
    if not batch_code or not isinstance(batch_code, str):
        return "unknown"

    batch = batch_code.strip().upper()

    # SI Factory format: D6067K or F6043A
    if re.match(r'^[DF]\d{4}[A-Z]$', batch):
        return "si_factory"

    # Standard format: RM-YYMMDD-NNNN or PR-YYMMDD-NNNN
    if re.match(r'^(RM|PR)-\d{6}-\d{4}$', batch):
        return "standard"

    # Julian date format without prefix
    if re.match(r'^\d{4,5}[A-Z]?$', batch):
        return "julian"

    return "unknown"
