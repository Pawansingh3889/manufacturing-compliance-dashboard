"""Manufacturing Compliance Dashboard — BRC/HACCP compliance for food manufacturing."""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import yaml
import json

from modules.traceability import trace_batch, get_traceability_score, get_recent_batches
from modules.temperature import (
    get_latest_readings, get_excursions, get_temperature_trend, get_compliance_score
)
from modules.allergens import get_allergen_matrix, get_allergen_summary
from modules.excel_parser import parse_upload, validate_temperature_upload
from modules.report_generator import generate_audit_report

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

    # Data upload
    st.markdown("### :open_file_folder: Upload Data")
    uploaded = st.file_uploader("Upload Excel/CSV", type=["csv", "xlsx", "xls"],
                                 help="Upload temperature logs, production data, or raw materials")
    if uploaded:
        df, error = parse_upload(uploaded)
        if error:
            st.error(error)
        else:
            st.success(f"Loaded {len(df)} rows from {uploaded.name}")
            st.dataframe(df.head(10), use_container_width=True)

    st.divider()
    st.caption("Built by [Pawan Singh Kapkoti](https://pawansingh3889.github.io)")

# === MAIN CONTENT ===
tab1, tab2, tab3, tab4 = st.tabs([
    ":link: Batch Traceability",
    ":thermometer: Temperature",
    ":warning: Allergens",
    ":page_facing_up: Audit Report",
])

# === TAB 1: BATCH TRACEABILITY ===
with tab1:
    st.header("Batch Traceability")
    st.caption("Trace any batch from raw material intake through production to customer dispatch.")

    col1, col2 = st.columns([1, 2])

    with col1:
        batch_code = st.text_input("Enter batch code", placeholder="e.g. RM-260301-0001 or PR-260301-0001")

        if st.button("Trace Batch", type="primary", use_container_width=True):
            if batch_code:
                result = trace_batch(batch_code)
                if result["found"]:
                    st.success(f"Batch {batch_code} found")

                    if "raw_materials" in result and not result["raw_materials"].empty:
                        st.subheader("Raw Materials")
                        st.dataframe(result["raw_materials"], use_container_width=True)

                    if "production" in result and not result["production"].empty:
                        st.subheader("Production")
                        st.dataframe(result["production"], use_container_width=True)

                    if "orders" in result and not result["orders"].empty:
                        st.subheader("Customer Orders")
                        st.dataframe(result["orders"], use_container_width=True)
                    else:
                        st.info("No customer orders linked to this batch yet.")
                else:
                    st.error(f"Batch {batch_code} not found. Try RM-YYMMDD-NNNN or PR-YYMMDD-NNNN format.")

    with col2:
        st.subheader("Recent Batches")
        recent = get_recent_batches(15)
        if not recent.empty:
            st.dataframe(
                recent,
                use_container_width=True,
                column_config={
                    "yield_pct": st.column_config.ProgressColumn("Yield %", min_value=0, max_value=100),
                },
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
            st.dataframe(excursions, use_container_width=True)

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
            st.plotly_chart(fig, use_container_width=True)

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
        st.dataframe(styled, use_container_width=True, height=400)

        # Export
        csv = display.to_csv(index=False)
        st.download_button("Download CSV", csv, "allergen_matrix.csv", "text/csv", use_container_width=True)

# === TAB 4: AUDIT REPORT ===
with tab4:
    st.header("Audit Report")
    st.caption(f"Generate a {STANDARD} compliance report for the last 30 days.")

    if st.button("Generate Report", type="primary", use_container_width=True):
        with st.spinner("Generating audit report..."):
            excursions = get_excursions(30)
            matrix = get_allergen_matrix()

            report = generate_audit_report(
                temp_score=temp_score,
                trace_score=trace_score,
                excursions=excursions,
                allergen_matrix=matrix,
                production_summary=None,
            )

            # Display scores
            status_color = "green" if report["compliance_scores"]["status"] == "PASS" else "red"
            st.markdown(f"### Status: :{status_color}[{report['compliance_scores']['status']}]")

            col1, col2, col3 = st.columns(3)
            col1.metric("Temperature", report["compliance_scores"]["temperature_control"])
            col2.metric("Traceability", report["compliance_scores"]["batch_traceability"])
            col3.metric("Overall", report["compliance_scores"]["overall"])

            st.divider()

            # Details
            st.subheader("Excursions in Period")
            if not excursions.empty:
                st.dataframe(excursions, use_container_width=True)
            else:
                st.success("No excursions in the last 30 days.")

            st.subheader("Allergen Matrix")
            st.dataframe(matrix, use_container_width=True)

            st.divider()

            # Export options
            st.subheader("Export")
            st.download_button(
                "Download Report (JSON)",
                json.dumps(report, indent=2, default=str),
                "audit_report.json",
                "application/json",
                use_container_width=True,
            )
            st.info("PDF and Excel export available in the [premium version](https://pawankapko.gumroad.com/).")
