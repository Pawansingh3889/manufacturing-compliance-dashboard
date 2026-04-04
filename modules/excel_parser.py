"""Excel/CSV file upload and parsing for data ingestion."""
import pandas as pd
import io


def parse_upload(uploaded_file):
    """Parse an uploaded Excel or CSV file and return a DataFrame."""
    filename = uploaded_file.name.lower()

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(uploaded_file)
        else:
            return None, f"Unsupported file type: {filename}. Use .csv, .xlsx, or .xls"

        return df, None
    except Exception as e:
        return None, f"Error reading file: {str(e)}"


def validate_temperature_upload(df):
    """Validate a temperature log upload has required columns."""
    required = ["location", "temperature", "recorded_at"]
    missing = [c for c in required if c not in [col.lower().replace(" ", "_") for col in df.columns]]

    if missing:
        return False, f"Missing columns: {', '.join(missing)}. Required: {', '.join(required)}"

    # Standardise column names
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
    df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce")

    invalid = df["temperature"].isna().sum()
    if invalid > 0:
        return True, f"Warning: {invalid} rows have non-numeric temperatures (will be skipped)"

    return True, f"Valid: {len(df)} temperature records found"


def validate_production_upload(df):
    """Validate a production data upload."""
    required = ["batch_code", "date", "raw_input_kg", "finished_output_kg"]
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
    missing = [c for c in required if c not in df.columns]

    if missing:
        return False, f"Missing columns: {', '.join(missing)}"

    return True, f"Valid: {len(df)} production records found"


def validate_raw_materials_upload(df):
    """Validate a raw materials upload."""
    required = ["batch_code", "supplier", "quantity_kg", "received_date"]
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
    missing = [c for c in required if c not in df.columns]

    if missing:
        return False, f"Missing columns: {', '.join(missing)}"

    return True, f"Valid: {len(df)} raw material records found"
