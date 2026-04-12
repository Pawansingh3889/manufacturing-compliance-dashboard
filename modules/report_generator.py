"""PDF Audit Report Generator for Manufacturing Compliance Dashboard.

Generates professional BRC/HACCP audit reports as in-memory byte streams.
No files written to disk — compatible with read-only deployments.
"""
from datetime import datetime

import pandas as pd
from fpdf import FPDF


class AuditReportPDF(FPDF):
    """Custom PDF class with professional header/footer for audit reports."""

    def __init__(self, factory_name, report_title):
        super().__init__()
        self.factory_name = factory_name
        self.report_title = report_title
        self.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._table_headers = []

    def header(self):
        # Navy bar at top
        self.set_fill_color(15, 23, 42)
        self.rect(0, 0, 210, 12, "F")

        # Factory name
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 2)
        self.cell(0, 8, self.factory_name, align="L")

        # Report title
        self.set_text_color(148, 163, 184)
        self.set_font("Helvetica", "", 8)
        self.set_xy(10, 6)
        self.cell(0, 8, self.report_title, align="R")

        self.ln(16)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f"Generated: {self.generated_at}", align="L")
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="R")

    def section_title(self, title):
        """Add a section header with underline."""
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(15, 23, 42)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        # Underline
        self.set_draw_color(37, 99, 235)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def metric_card(self, label, value, status=""):
        """Add a KPI metric inline."""
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 116, 139)
        self.cell(45, 5, label, new_x="END")

        self.set_font("Helvetica", "B", 11)
        self.set_text_color(15, 23, 42)
        self.cell(25, 5, str(value), new_x="END")

        if status:
            if status == "PASS":
                self.set_text_color(22, 163, 74)
            else:
                self.set_text_color(185, 28, 28)
            self.set_font("Helvetica", "B", 9)
            self.cell(15, 5, status, new_x="LMARGIN", new_y="NEXT")
        else:
            self.ln(5)

    def add_dataframe_table(self, df, col_widths=None, max_rows=500):
        """Render a DataFrame as a formatted table with automatic page breaks.

        - Headers repeat on each new page
        - Dates formatted cleanly
        - Handles pagination for large datasets
        """
        if df.empty:
            self.set_font("Helvetica", "I", 9)
            self.set_text_color(100, 116, 139)
            self.cell(0, 8, "No data available.", new_x="LMARGIN", new_y="NEXT")
            return

        # Limit rows
        if len(df) > max_rows:
            df = df.head(max_rows)

        # Format date columns
        df = _format_dates(df.copy())

        # Calculate column widths
        columns = list(df.columns)
        if col_widths is None:
            available = 190  # A4 width minus margins
            col_widths = [available / len(columns)] * len(columns)

        # Truncate column names if too wide
        self._table_headers = columns
        self._table_col_widths = col_widths

        # Draw header
        self._draw_table_header(columns, col_widths)

        # Draw rows
        self.set_font("Helvetica", "", 7)
        row_height = 6
        fill = False

        for _, row in df.iterrows():
            # Check if we need a new page
            if self.get_y() + row_height > 270:
                self.add_page()
                self._draw_table_header(columns, col_widths)
                self.set_font("Helvetica", "", 7)

            # Alternate row background
            if fill:
                self.set_fill_color(248, 250, 252)
            else:
                self.set_fill_color(255, 255, 255)

            self.set_text_color(30, 41, 59)

            for i, col in enumerate(columns):
                val = str(row[col]) if pd.notna(row[col]) else ""
                # Truncate long values
                if len(val) > 30:
                    val = val[:27] + "..."
                self.cell(col_widths[i], row_height, val, border=1, fill=True, new_x="END")

            self.ln(row_height)
            fill = not fill

    def _draw_table_header(self, columns, col_widths):
        """Draw table header row (called on each page)."""
        self.set_font("Helvetica", "B", 7)
        self.set_fill_color(15, 23, 42)
        self.set_text_color(255, 255, 255)
        row_height = 7

        for i, col in enumerate(columns):
            display = str(col).replace("_", " ").title()
            if len(display) > 20:
                display = display[:17] + "..."
            self.cell(col_widths[i], row_height, display, border=1, fill=True, new_x="END")

        self.ln(row_height)
        self.set_text_color(30, 41, 59)

    def add_text(self, text, bold=False):
        """Add a paragraph of body text."""
        self.set_font("Helvetica", "B" if bold else "", 9)
        self.set_text_color(51, 65, 85)
        self.multi_cell(0, 5, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)


def _format_dates(df):
    """Format datetime columns to clean readable strings."""
    for col in df.columns:
        if df[col].dtype == "object":
            try:
                parsed = pd.to_datetime(df[col], errors="coerce")
                if parsed.notna().sum() > len(df) * 0.5:
                    df[col] = parsed.dt.strftime("%Y-%m-%d %H:%M").fillna(df[col])
            except Exception:
                pass
    return df


def generate_audit_report(dataframe, report_title, factory_name="Fish Processing Facility"):
    """Generate a PDF audit report from a DataFrame.

    Returns bytes — no file written to disk. Safe for read-only deployments.

    Args:
        dataframe: pandas DataFrame to render as a table
        report_title: Title for the report (e.g., "Batch Traceability Report")
        factory_name: Facility name shown in header

    Returns:
        bytes: PDF file content ready for st.download_button
    """
    pdf = AuditReportPDF(factory_name, report_title)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Title
    pdf.section_title(report_title)
    pdf.add_text(f"Facility: {factory_name}")
    pdf.add_text(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    pdf.add_text(f"Records: {len(dataframe)}")
    pdf.ln(4)

    # Table
    pdf.add_dataframe_table(dataframe)

    # Return as bytes — never touches the filesystem
    return bytes(pdf.output())


def generate_full_audit_report(
    factory_name,
    temp_score,
    trace_score,
    excursions_df,
    allergen_df,
    shelf_life_summary,
    concessions_df,
    recent_batches_df,
):
    """Generate a comprehensive multi-section BRC audit report.

    Returns bytes — no file written to disk.
    """
    pdf = AuditReportPDF(factory_name, "BRC Compliance Audit Report")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    # === COVER PAGE ===
    pdf.add_page()
    pdf.ln(40)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 15, "BRC Compliance", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 15, "Audit Report", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 10, factory_name, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, datetime.now().strftime("%B %Y"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(20)

    overall = round((temp_score + trace_score) / 2, 1)
    status = "PASS" if overall >= 85 else "FAIL"
    pdf.set_font("Helvetica", "B", 20)
    if status == "PASS":
        pdf.set_text_color(22, 163, 74)
    else:
        pdf.set_text_color(185, 28, 28)
    pdf.cell(0, 15, f"Overall: {overall}% - {status}", align="C", new_x="LMARGIN", new_y="NEXT")

    # === COMPLIANCE SCORES ===
    pdf.add_page()
    pdf.section_title("1. Compliance Scores")
    pdf.metric_card("Temperature Control", f"{temp_score}%", "PASS" if temp_score >= 85 else "FAIL")
    pdf.metric_card("Batch Traceability", f"{trace_score}%", "PASS" if trace_score >= 85 else "FAIL")
    pdf.metric_card("Overall", f"{overall}%", status)
    pdf.ln(6)

    if shelf_life_summary:
        pdf.metric_card("Batches (30 days)", str(shelf_life_summary.get("total_batches", 0)))
        pdf.metric_card("Within Spec", str(shelf_life_summary.get("within_spec", 0)))
        pdf.metric_card("Concessions Required", str(shelf_life_summary.get("concessions", 0)))
        pdf.metric_card("Shelf Life Compliance", f"{shelf_life_summary.get('compliance_pct', 0)}%")

    # === TEMPERATURE EXCURSIONS ===
    pdf.add_page()
    pdf.section_title("2. Temperature Excursions (30 Days)")
    if excursions_df is not None and not excursions_df.empty:
        pdf.add_text(f"{len(excursions_df)} excursion(s) detected in the reporting period.")
        pdf.add_dataframe_table(excursions_df)
    else:
        pdf.add_text("No temperature excursions detected. All readings within specification.")

    # === ALLERGEN MATRIX ===
    pdf.add_page()
    pdf.section_title("3. Allergen Matrix")
    if allergen_df is not None and not allergen_df.empty:
        pdf.add_text(f"{len(allergen_df)} products tracked.")
        pdf.add_dataframe_table(allergen_df)
    else:
        pdf.add_text("No allergen data available.")

    # === CONCESSIONS ===
    if concessions_df is not None and not concessions_df.empty:
        pdf.add_page()
        pdf.section_title("4. Shelf Life Concessions")
        pdf.add_text(f"{len(concessions_df)} concession(s) in the reporting period.")
        pdf.add_dataframe_table(concessions_df)

    # === RECENT BATCHES ===
    if recent_batches_df is not None and not recent_batches_df.empty:
        pdf.add_page()
        pdf.section_title("5. Recent Production Batches")
        pdf.add_dataframe_table(recent_batches_df, max_rows=50)

    return bytes(pdf.output())
