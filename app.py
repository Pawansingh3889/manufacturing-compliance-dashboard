"""Manufacturing Compliance Dashboard — BRC/HACCP compliance for food manufacturing."""
import os
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import yaml
import json
from datetime import datetime

# Auto-seed demo database if it doesn't exist
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "compliance.db")
if not os.path.exists(DB_PATH):
    from data.seed_demo import seed
    seed()

from modules.traceability import trace_batch, get_traceability_score, get_recent_batches
from modules.temperature import (
    get_latest_readings, get_excursions, get_temperature_trend, get_compliance_score
)
from modules.allergens import get_allergen_matrix, get_allergen_summary
from modules.excel_parser import parse_upload, validate_temperature_upload
from modules.report_generator import generate_audit_report, generate_full_audit_report
from modules.shelf_life import (
    get_expiring_soon, get_expired, get_concessions,
    get_shelf_life_summary, decode_batch_code
)

# === CONFIG ===
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

FACILITY = config["facility"]["name"]
STANDARD = config["facility"]["standard"]

st.set_page_config(
    page_title=f"Compliance Dashboard | {FACILITY}",
    page_icon=":shield:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# === SIDEBAR ===
with st.sidebar:
    st.markdown(f"## :shield: Compliance")
    st.caption(f"{FACILITY}")
    st.caption(f"Standard: {STANDARD}")
    st.divider()

    # KPI Scores
    temp_score = get_compliance_score()
    trace_score = get_traceability_score()
    overall = round((temp_score + trace_score) / 2, 1)

    st.metric("Temperature Control", f"{temp_score}%",
              delta="PASS" if temp_score >= 85 else "FAIL",
              delta_color="normal" if temp_score >= 85 else "inverse")
    st.metric("Batch Traceability", f"{trace_score}%",
              delta="PASS" if trace_score >= 85 else "FAIL",
              delta_color="normal" if trace_score >= 85 else "inverse")
    st.divider()
    st.metric("Overall Compliance", f"{overall}%",
              delta="PASS" if overall >= 85 else "FAIL",
              delta_color="normal" if overall >= 85 else "inverse")

    st.divider()

    # ERP Data Import
    st.markdown("### :open_file_folder: Import ERP Data")
    data_type = st.selectbox("Data type", ["production", "raw_materials", "temperature"],
                              format_func=lambda x: x.replace("_", " ").title())
    uploaded = st.file_uploader("Drop your ERP export here", type=["csv", "xlsx", "xls"],
                                 help="Supports SI Integreater, Aptean, and generic BRC exports. Columns are auto-mapped.")
    if uploaded:
        from modules.erp_parser import parse_erp_file
        mapped_df, report = parse_erp_file(uploaded, data_type)
        if "error" in report:
            st.error(report["error"])
        else:
            st.success(f"Mapped {report['mapped_count']}/{report['total_columns']} columns from {report['source']}")
            if report["unmapped"]:
                st.warning(f"Unmapped columns: {', '.join(report['unmapped'])}")
            with st.expander("Column mapping"):
                for orig, mapped in report["mapped"].items():
                    st.text(f"{orig} -> {mapped}")
            st.dataframe(mapped_df.head(10), width='stretch')

    st.divider()
    st.caption("Built by [Pawan Singh Kapkoti](https://pawansingh3889.github.io)")

# === MAIN CONTENT ===
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    ":link: Batch Traceability",
    ":thermometer: Temperature",
    ":warning: Allergens",
    ":calendar: Shelf Life",
    ":page_facing_up: Audit Report",
])

# === TAB 1: BATCH TRACEABILITY ===
with tab1:
    st.header("Batch Traceability")
    st.caption("Trace any batch from raw material intake through production to customer dispatch.")

    col1, col2 = st.columns([1, 2])

    with col1:
        batch_code = st.text_input("Enter batch code", placeholder="e.g. F6093E or D6067K")

        if st.button("Trace Batch", type="primary", width='stretch'):
            if batch_code:
                result = trace_batch(batch_code)
                if result["found"]:
                    st.success(f"Batch {batch_code} found")

                    if "raw_materials" in result and not result["raw_materials"].empty:
                        st.subheader("Raw Materials")
                        st.dataframe(result["raw_materials"], width='stretch')

                    if "production" in result and not result["production"].empty:
                        st.subheader("Production")
                        st.dataframe(result["production"], width='stretch')

                    if "orders" in result and not result["orders"].empty:
                        st.subheader("Customer Orders")
                        st.dataframe(result["orders"], width='stretch')
                    else:
                        st.info("No customer orders linked to this batch yet.")
                else:
                    st.error(f"Batch {batch_code} not found. Try formats like F6093E, D6067K, or click a batch code from the table.")

    with col2:
        st.subheader("Recent Batches")
        recent = get_recent_batches(15)
        if not recent.empty:
            st.dataframe(
                recent,
                width='stretch',
                column_config={
                    "yield_pct": st.column_config.ProgressColumn("Yield %", min_value=0, max_value=100),
                },
            )

            # PDF Export
            with st.expander("Export Audit Report (PDF)"):
                if st.button("Generate Traceability PDF", key="trace_pdf"):
                    pdf_bytes = generate_audit_report(recent, "Batch Traceability Report", FACILITY)
                    st.download_button(
                        "Download PDF",
                        data=pdf_bytes,
                        file_name="traceability_audit_report.pdf",
                        mime="application/pdf",
                        key="trace_dl",
                    )

# === TAB 2: TEMPERATURE MONITORING ===
with tab2:
    st.header("Temperature Monitoring")

    # Current readings
    st.subheader("Current Readings")
    latest = get_latest_readings()
    if not latest.empty:
        thresholds = config["temperature"]["locations"]
        cols = st.columns(len(latest))
        for i, (_, row) in enumerate(latest.iterrows()):
            loc = row["location"]
            temp = row["temperature"]
            limits = thresholds.get(loc, {"min": -999, "max": 999})
            in_range = limits["min"] <= temp <= limits["max"]

            with cols[i]:
                st.metric(
                    loc,
                    f"{temp:.1f} C",
                    delta="OK" if in_range else "EXCURSION",
                    delta_color="normal" if in_range else "inverse",
                )

    # Excursions
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Excursions (Last 7 Days)")
        excursions = get_excursions(7)
        if excursions.empty:
            st.success("No temperature excursions in the last 7 days.")
        else:
            st.warning(f"{len(excursions)} excursion(s) detected!")
            st.dataframe(excursions, width='stretch')

    with col2:
        st.subheader("Temperature Trend")
        locations = list(config["temperature"]["locations"].keys())
        selected_loc = st.selectbox("Select location", locations)
        trend = get_temperature_trend(selected_loc, 30)

        if not trend.empty:
            limits = config["temperature"]["locations"][selected_loc]
            fig = px.line(trend, x="recorded_at", y="temperature",
                         title=f"{selected_loc} — Last 30 Days")
            fig.add_hline(y=limits["max"], line_dash="dash", line_color="red",
                         annotation_text=f"Max: {limits['max']}C")
            fig.add_hline(y=limits["min"], line_dash="dash", line_color="blue",
                         annotation_text=f"Min: {limits['min']}C")
            fig.update_layout(height=400, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, width='stretch')

    # PDF Export for temperature
    with st.expander("Export Temperature Report (PDF)"):
        if st.button("Generate Temperature PDF", key="temp_pdf"):
            temp_excursions_30d = get_excursions(30)
            pdf_bytes = generate_audit_report(temp_excursions_30d, "Temperature Excursion Report (30 Days)", FACILITY)
            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name="temperature_excursion_report.pdf",
                mime="application/pdf",
                key="temp_dl",
            )

# === TAB 3: ALLERGEN MATRIX ===
with tab3:
    st.header("Allergen Matrix")
    st.caption("Cross-reference of products and allergens. Required for BRC Section 5.")

    matrix = get_allergen_matrix()
    if not matrix.empty:
        # Summary
        summary = get_allergen_summary()
        cols = st.columns(min(len(summary), 6))
        for i, (allergen, count) in enumerate(list(summary.items())[:6]):
            with cols[i]:
                st.metric(allergen, f"{count} products")

        st.divider()

        # Filter
        categories = ["All"] + sorted(matrix["Category"].unique().tolist())
        selected_cat = st.selectbox("Filter by category", categories)

        display = matrix if selected_cat == "All" else matrix[matrix["Category"] == selected_cat]

        # Highlight cells with allergens
        def highlight_allergens(val):
            return "background-color: #fee2e2; color: #991b1b; font-weight: bold" if val == "Y" else ""

        allergen_cols = [c for c in display.columns if c not in ["Product", "Species", "Category", "Total Allergens"]]
        styled = display.style.map(highlight_allergens, subset=allergen_cols)
        st.dataframe(styled, width='stretch', height=400)

        # Export
        csv = display.to_csv(index=False)
        st.download_button("Download CSV", csv, "allergen_matrix.csv", "text/csv", width='stretch')

# === TAB 4: SHELF LIFE & CONCESSIONS ===
with tab4:
    st.header("Shelf Life & Concessions")
    st.caption("Track use-by dates. Fresh = +19 days (superchill). Defrost = +11 days (chiller). Beyond = concession required.")

    # Summary
    sl_summary = get_shelf_life_summary()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Batches (30d)", sl_summary["total_batches"])
    col2.metric("Within Spec", sl_summary["within_spec"])
    col3.metric("Concessions", sl_summary["concessions"],
                delta="OK" if sl_summary["concessions"] == 0 else f"{sl_summary['concessions']} needed",
                delta_color="normal" if sl_summary["concessions"] == 0 else "inverse")
    col4.metric("Compliance", f"{sl_summary['compliance_pct']}%")

    st.divider()

    # Batch code decoder
    st.subheader("Batch Code Decoder")
    decode_input = st.text_input("Enter batch code to decode", placeholder="e.g. D6067K or F6043A")
    if decode_input:
        decoded = decode_batch_code(decode_input)
        if decoded:
            dcol1, dcol2, dcol3, dcol4 = st.columns(4)
            dcol1.metric("Type", decoded["product_type"])
            dcol2.metric("Pack Date", decoded["pack_date"])
            dcol3.metric("Use By", decoded["use_by_date"])
            dcol4.metric("Storage", decoded["storage"])
            st.info(f"Shelf life: {decoded['shelf_life_days']} days. Sub-batch: {decoded['sub_batch'] or 'N/A'}")
        else:
            st.error("Invalid batch code format. Expected D/F + YDDD + letter (e.g. D6067K)")

    st.divider()

    # Expiring soon
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Expiring Within 3 Days")
        expiring = get_expiring_soon(3)
        if expiring.empty:
            st.success("No batches expiring in the next 3 days.")
        else:
            st.warning(f"{len(expiring)} batch(es) expiring soon!")
            st.dataframe(expiring, width='stretch',
                        column_config={
                            "days_remaining": st.column_config.NumberColumn("Days Left", format="%d"),
                        })

    with col2:
        st.subheader("Concessions (Last 30 Days)")
        concessions = get_concessions(30)
        if concessions.empty:
            st.success("No concessions required in the last 30 days.")
        else:
            st.dataframe(concessions, width='stretch')

# === TAB 5: AUDIT REPORT ===
with tab5:
    st.header("Audit Report")
    st.caption(f"Generate a {STANDARD} compliance report for the last 30 days.")

    if st.button("Generate Full Audit Report", type="primary"):
        with st.spinner("Generating audit report..."):
            excursions_30d = get_excursions(30)
            allergen_matrix = get_allergen_matrix()
            sl_summary = get_shelf_life_summary()
            concessions_30d = get_concessions(30)
            recent = get_recent_batches(50)

            overall = round((temp_score + trace_score) / 2, 1)
            status = "PASS" if overall >= 85 else "FAIL"

            # Display scores
            status_color = "green" if status == "PASS" else "red"
            st.markdown(f"### Status: :{status_color}[{status}]")

            col1, col2, col3 = st.columns(3)
            col1.metric("Temperature", f"{temp_score}%")
            col2.metric("Traceability", f"{trace_score}%")
            col3.metric("Overall", f"{overall}%")

            st.divider()

            st.subheader("Excursions in Period")
            if not excursions_30d.empty:
                st.dataframe(excursions_30d, width='stretch')
            else:
                st.success("No excursions in the last 30 days.")

            st.subheader("Allergen Matrix")
            st.dataframe(allergen_matrix, width='stretch')

            st.divider()

            # PDF Export
            st.subheader("Export")

            pdf_bytes = generate_full_audit_report(
                factory_name=FACILITY,
                temp_score=temp_score,
                trace_score=trace_score,
                excursions_df=excursions_30d,
                allergen_df=allergen_matrix,
                shelf_life_summary=sl_summary,
                concessions_df=concessions_30d,
                recent_batches_df=recent,
            )

            st.download_button(
                "Download Full Audit Report (PDF)",
                data=pdf_bytes,
                file_name=f"brc_audit_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
            )
