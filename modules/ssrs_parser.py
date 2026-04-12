"""SSRS (SQL Server Reporting Services) Export Parser.

SI Integreater uses SSRS for report generation. SSRS Excel exports have
specific formatting that standard pandas.read_excel() doesn't handle well:

- Report header rows (title, parameters, date range)
- Merged cells for group headers
- Multiple sheets per report
- Blank separator rows between sections
- Footer rows with totals

This module strips SSRS formatting and extracts clean data.
"""
import re

import pandas as pd


def detect_ssrs_format(df):
    """Detect if a DataFrame looks like an SSRS Excel export.

    SSRS exports typically have:
    - First few rows are report metadata (title, date, parameters)
    - A row that looks like column headers (usually row 3-8)
    - Data starts after the header row
    - Last rows may be totals/footer
    """
    if df.empty or len(df) < 5:
        return False, 0

    # Check for SSRS telltale signs in first 10 rows
    for i in range(min(10, len(df))):
        row = df.iloc[i]
        row_str = " ".join(str(v) for v in row if pd.notna(v)).lower()

        # SSRS reports often have "report", "generated", "page", "date" in headers
        if any(kw in row_str for kw in ["report", "generated", "printed", "page 1"]):
            continue

        # Check if this row looks like column headers
        non_null = row.notna().sum()
        if non_null >= 3:
            # Check if values look like headers (short strings, no numbers)
            header_like = sum(
                1 for v in row if pd.notna(v) and isinstance(v, str) and len(v) < 30
            )
            if header_like >= 3:
                return True, i

    return False, 0


def clean_ssrs_excel(filepath_or_buffer, sheet_name=0):
    """Read an SSRS Excel export and return clean DataFrames.

    Handles:
    - Skipping report header rows
    - Finding the real column headers
    - Removing blank separator rows
    - Removing total/footer rows
    - Cleaning merged cell artifacts (NaN fill-down)

    Args:
        filepath_or_buffer: File path or Streamlit UploadedFile
        sheet_name: Sheet index or name (default: 0 for first sheet)

    Returns:
        tuple: (clean_df, metadata_dict)
    """
    # First read: get everything raw to find the structure
    raw = pd.read_excel(filepath_or_buffer, sheet_name=sheet_name, header=None)

    if raw.empty:
        return pd.DataFrame(), {"error": "Empty file"}

    # Extract metadata from header rows
    metadata = _extract_metadata(raw)

    # Find the real header row
    is_ssrs, header_row = detect_ssrs_format(raw)

    if is_ssrs:
        # Re-read with correct header
        if hasattr(filepath_or_buffer, 'seek'):
            filepath_or_buffer.seek(0)
        df = pd.read_excel(
            filepath_or_buffer,
            sheet_name=sheet_name,
            header=header_row
        )
    else:
        # Not SSRS format — use first row as header
        if hasattr(filepath_or_buffer, 'seek'):
            filepath_or_buffer.seek(0)
        df = pd.read_excel(filepath_or_buffer, sheet_name=sheet_name)

    # Clean up
    df = _clean_dataframe(df)

    metadata["is_ssrs"] = is_ssrs
    metadata["header_row"] = header_row
    metadata["rows"] = len(df)
    metadata["columns"] = list(df.columns)

    return df, metadata


def clean_ssrs_csv(filepath_or_buffer):
    """Read an SSRS CSV export and return clean data.

    SSRS CSVs are simpler than Excel — usually no merged cells.
    But they may still have header rows and footer totals.
    """
    # Try reading with different encodings
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            if hasattr(filepath_or_buffer, 'seek'):
                filepath_or_buffer.seek(0)
            raw = pd.read_csv(filepath_or_buffer, encoding=encoding, header=None)
            if len(raw.columns) > 1:
                break
        except Exception:
            continue

    if raw.empty:
        return pd.DataFrame(), {"error": "Empty file"}

    metadata = _extract_metadata(raw)
    is_ssrs, header_row = detect_ssrs_format(raw)

    if is_ssrs and header_row > 0:
        if hasattr(filepath_or_buffer, 'seek'):
            filepath_or_buffer.seek(0)
        df = pd.read_csv(
            filepath_or_buffer,
            encoding=encoding,
            header=header_row,
            skip_blank_lines=True
        )
    else:
        if hasattr(filepath_or_buffer, 'seek'):
            filepath_or_buffer.seek(0)
        df = pd.read_csv(filepath_or_buffer, encoding=encoding)

    df = _clean_dataframe(df)

    metadata["is_ssrs"] = is_ssrs
    metadata["header_row"] = header_row
    metadata["rows"] = len(df)
    metadata["columns"] = list(df.columns)

    return df, metadata


def _extract_metadata(raw_df):
    """Extract report metadata from SSRS header rows."""
    metadata = {}

    for i in range(min(8, len(raw_df))):
        row_str = " ".join(str(v) for v in raw_df.iloc[i] if pd.notna(v))

        # Extract report title
        if i == 0 and len(row_str) > 5:
            metadata["report_title"] = row_str.strip()

        # Extract date/time
        date_match = re.search(
            r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
            row_str
        )
        if date_match and "report_date" not in metadata:
            metadata["report_date"] = date_match.group(1)

        # Extract "Generated" timestamp
        gen_match = re.search(
            r'(?:generated|printed|run)\s*:?\s*(.+)',
            row_str,
            re.IGNORECASE
        )
        if gen_match:
            metadata["generated"] = gen_match.group(1).strip()

    return metadata


def _clean_dataframe(df):
    """Clean up common SSRS artifacts in a DataFrame."""
    # Remove completely empty rows
    df = df.dropna(how="all")

    # Remove rows where all values are the same (separator rows)
    df = df[~df.apply(lambda row: row.nunique() == 1 and pd.isna(row.iloc[0]), axis=1)]

    # Remove footer/total rows (often contain "Total", "Grand Total", "Page")
    if len(df) > 0:
        last_rows_to_check = min(5, len(df))
        for i in range(len(df) - 1, max(len(df) - last_rows_to_check - 1, -1), -1):
            row_str = " ".join(str(v) for v in df.iloc[i] if pd.notna(v)).lower()
            if any(kw in row_str for kw in ["total", "grand total", "page ", "end of report"]):
                df = df.iloc[:i]
                break

    # Clean column names
    df.columns = [
        str(c).strip().replace("\n", " ").replace("  ", " ")
        for c in df.columns
    ]

    # Remove unnamed columns (artifacts from merged cells)
    unnamed = [c for c in df.columns if c.lower().startswith("unnamed")]
    if unnamed:
        # Only drop if they're entirely empty
        to_drop = [c for c in unnamed if df[c].isna().all()]
        df = df.drop(columns=to_drop)

    # Forward-fill merged cell values (SSRS leaves NaN where cells are merged)
    for col in df.columns:
        if df[col].dtype == "object":
            # Only fill if the column has a pattern of value-then-blanks
            non_null_pct = df[col].notna().mean()
            if 0.1 < non_null_pct < 0.6:
                df[col] = df[col].ffill()

    # Reset index
    df = df.reset_index(drop=True)

    return df


def get_all_sheets(filepath_or_buffer):
    """Get a list of sheet names from an Excel file."""
    try:
        xl = pd.ExcelFile(filepath_or_buffer)
        return xl.sheet_names
    except Exception:
        return []


def parse_ssrs_file(uploaded_file):
    """Auto-detect and parse an SSRS export (Excel or CSV).

    Returns:
        tuple: (DataFrame, metadata_dict)
    """
    filename = uploaded_file.name.lower()

    if filename.endswith((".xlsx", ".xls")):
        return clean_ssrs_excel(uploaded_file)
    elif filename.endswith(".csv"):
        return clean_ssrs_csv(uploaded_file)
    else:
        return pd.DataFrame(), {"error": f"Unsupported format: {filename}"}
