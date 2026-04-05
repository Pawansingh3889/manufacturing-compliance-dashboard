"""Manufacturing Compliance Dashboard - BRC/HACCP Compliance for Food Manufacturing."""
import os
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import yaml
import json
from datetime import datetime

# Auto-seed database — checks schema version
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "factory_compliance.db")
_needs_seed = not os.path.exists(DB_PATH)
if not _needs_seed:
    try:
        import sqlite3
        _conn = sqlite3.connect(DB_PATH)
        _cols = [r[1] for r in _conn.execute("PRAGMA table_info(batches)").fetchall()]
        _conn.close()
        if "life_days" not in _cols:
            os.remove(DB_PATH)
            _needs_seed = True
    except Exception:
        _needs_seed = True
if _needs_seed:
    from data.seed_demo import seed
    seed()

from modules.database import query, scalar, load_config

config = load_config()
FACILITY = config["facility"]["name"]

# === PAGE CONFIG ===
st.set_page_config(
    page_title=f"{FACILITY} | Compliance",
    page_icon=":shield:",
    layout="wide",
)

# === CUSTOM CSS ===
st.markdown("""
<style>
    /* Clean header */
    .stApp > header { background: transparent; }

    /* Card styling */
    div[data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 20px;
    }
    div[data-testid="stMetric"] label {
        color: #64748b;
        font-size: 0.85rem;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #0f172a;
        font-weight: 700;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 20px;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #0f172a;
    }
    section[data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stMetric"] {
        background: #1e293b;
        border-color: #334155;
    }
    section[data-testid="stSidebar"] div[data-testid="stMetric"] label {
        color: #94a3b8 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #ffffff !important;
    }

    /* Hide Streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# === COMPUTE SCORES ===
temp_total = scalar("SELECT COUNT(*) FROM temperature_logs WHERE timestamp >= date('now', '-30 days')") or 1
temp_ok = scalar("SELECT COUNT(*) FROM temperature_logs WHERE timestamp >= date('now', '-30 days') AND is_excursion = 0") or 0
temp_score = round((temp_ok / temp_total) * 100, 1) if temp_total > 0 else 0

batch_total = scalar("SELECT COUNT(*) FROM batches WHERE production_date >= date('now', '-30 days')") or 1
batch_linked = scalar("SELECT COUNT(*) FROM batches WHERE production_date >= date('now', '-30 days') AND raw_material_batch IS NOT NULL") or 0
trace_score = round((batch_linked / batch_total) * 100, 1) if batch_total > 0 else 0

overall = round((temp_score + trace_score) / 2, 1)

# === SIDEBAR ===
with st.sidebar:
    st.markdown("## :shield: Compliance")
    st.caption(FACILITY)
    st.caption(f"Standard: {config['facility']['standard']}")
    st.divider()

    st.metric("Temperature", f"{temp_score}%", delta="PASS" if temp_score >= 85 else "FAIL",
              delta_color="normal" if temp_score >= 85 else "inverse")
    st.metric("Traceability", f"{trace_score}%", delta="PASS" if trace_score >= 85 else "FAIL",
              delta_color="normal" if trace_score >= 85 else "inverse")
    st.metric("Overall", f"{overall}%", delta="PASS" if overall >= 85 else "FAIL",
              delta_color="normal" if overall >= 85 else "inverse")

    st.divider()
    st.markdown("### Import Data")
    data_type = st.selectbox("Data type", ["production", "raw_materials", "temperature"],
                              format_func=lambda x: x.replace("_", " ").title())
    uploaded = st.file_uploader("Drop ERP export", type=["csv", "xlsx", "xls"],
                                 help="Auto-maps columns from any food ERP")

    st.divider()
    st.caption(f"[pawansingh3889.github.io](https://pawansingh3889.github.io)")

# === MAIN ===
tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    ":truck:  FEFO Despatch",
    ":link:  Traceability",
    ":thermometer:  Temperature",
    ":warning:  Allergens",
    ":calendar:  Shelf Life",
    ":page_facing_up:  Audit",
])

# === FEFO DESPATCH PRIORITY ===
with tab0:
    st.markdown("### Despatch Priority (FEFO)")
    st.caption("First Expired, First Out. Standard shelf life ships before superchilled when both in stock.")

    # Get all in-stock batches — mirrors SI Stock Tracker view
    fefo = query("""
        SELECT b.batch_code, b.batch_no, b.run_number, b.trace_id,
               p.name as product, p.species, p.certification, p.shelf_life_type,
               b.age_days as "Age (Days)", b.life_days as "Life (Days)",
               b.stock_location as "Location", b.use_by_date as "Expiry",
               b.production_date as "Post Date",
               b.stock_kg as "Weight (kg)", b.stock_units as "Units",
               b.alert_flag as "Alert",
               CASE
                   WHEN b.life_days <= 3 THEN 'RED'
                   WHEN b.life_days <= 7 THEN 'AMBER'
                   ELSE 'GREEN'
               END as urgency
        FROM batches b
        JOIN products p ON b.product_id = p.id
        WHERE b.status = 'In Stock' AND b.stock_kg > 0
        ORDER BY
            CASE p.shelf_life_type WHEN 'standard' THEN 0 ELSE 1 END,
            b.life_days ASC
    """)

    if not fefo.empty:
        # KPI cards
        red = len(fefo[fefo["urgency"] == "RED"])
        amber = len(fefo[fefo["urgency"] == "AMBER"])
        green = len(fefo[fefo["urgency"] == "GREEN"])
        total_kg = round(fefo["Weight (kg)"].sum(), 0)
        total_units = int(fefo["Units"].sum())
        alerts = int(fefo["Alert"].sum()) if "Alert" in fefo.columns else 0

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("RED (<3 days)", red, delta="SHIP NOW" if red > 0 else "Clear",
                    delta_color="inverse" if red > 0 else "normal")
        col2.metric("AMBER (3-7d)", amber)
        col3.metric("GREEN (7+d)", green)
        col4.metric("Batches", len(fefo))
        col5.metric("Stock (kg)", f"{total_kg:,.0f}")
        col6.metric("Alerts", alerts, delta="CHECK" if alerts > 0 else "None",
                    delta_color="inverse" if alerts > 0 else "normal")

        st.divider()

        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            species_filter = st.selectbox("Species", ["All"] + sorted(fefo["species"].unique().tolist()), key="fefo_species")
        with col2:
            loc_filter = st.selectbox("Location", ["All"] + sorted(fefo["Location"].unique().tolist()), key="fefo_loc")
        with col3:
            cert_filter = st.selectbox("Certification", ["All"] + sorted(fefo["certification"].unique().tolist()), key="fefo_cert")

        display = fefo.copy()
        if species_filter != "All":
            display = display[display["species"] == species_filter]
        if loc_filter != "All":
            display = display[display["Location"] == loc_filter]
        if cert_filter != "All":
            display = display[display["certification"] == cert_filter]

        # Show SI-style columns
        show_cols = ["batch_code", "run_number", "product", "Age (Days)", "Life (Days)",
                     "Location", "Expiry", "Weight (kg)", "Units", "certification",
                     "shelf_life_type", "urgency", "Alert"]

        # Colour-coded table
        def colour_urgency(val):
            if val == "RED":
                return "background-color: #fee2e2; color: #991b1b; font-weight: bold"
            elif val == "AMBER":
                return "background-color: #fef3c7; color: #92400e; font-weight: bold"
            elif val == "GREEN":
                return "background-color: #dcfce7; color: #166534"
            return ""

        def colour_life(val):
            try:
                v = int(val)
                if v <= 3: return "background-color: #fee2e2; color: #991b1b; font-weight: bold"
                if v <= 7: return "background-color: #fef3c7; color: #92400e"
            except: pass
            return ""

        def colour_shelf_type(val):
            if val == "standard":
                return "background-color: #dbeafe; font-weight: bold"
            return ""

        def colour_alert(val):
            if val: return "background-color: #fee2e2; font-weight: bold"
            return ""

        visible = display[[c for c in show_cols if c in display.columns]]
        styled = visible.style.map(colour_urgency, subset=["urgency"]) \
                              .map(colour_life, subset=["Life (Days)"]) \
                              .map(colour_shelf_type, subset=["shelf_life_type"]) \
                              .map(colour_alert, subset=["Alert"])
        st.dataframe(styled, use_container_width=True, height=500)

        # RSPCA/MSC mismatch check
        st.divider()
        st.markdown("**Certification Allocation Check**")
        rspca_stock = fefo[fefo["certification"] == "RSPCA"]["Weight (kg)"].sum()
        msc_stock = fefo[fefo["certification"] == "MSC"]["Weight (kg)"].sum()
        std_stock = fefo[fefo["certification"] == "Standard"]["Weight (kg)"].sum()

        ccol1, ccol2, ccol3 = st.columns(3)
        ccol1.metric("RSPCA Stock", f"{rspca_stock:,.0f} kg")
        ccol2.metric("MSC Stock", f"{msc_stock:,.0f} kg")
        ccol3.metric("Standard Stock", f"{std_stock:,.0f} kg")

        if rspca_stock > 0 and std_stock > 0:
            st.warning("RSPCA-certified stock in inventory alongside standard stock. Ensure RSPCA product is allocated to RSPCA orders to avoid margin loss.")
    else:
        st.success("No stock currently in inventory.")

# === TRACEABILITY ===
with tab1:
    st.markdown("### Batch Traceability")

    col1, col2 = st.columns([1, 2])

    with col1:
        batch_input = st.text_input("Batch code", placeholder="e.g. F6093E or D6067K")
        if st.button("Trace", type="primary", use_container_width=True):
            if batch_input:
                batch_input = batch_input.strip().upper()
                prod = query(
                    "SELECT b.*, p.name as product_name, p.product_type, p.shelf_life_days "
                    "FROM batches b JOIN products p ON b.product_id = p.id "
                    "WHERE UPPER(b.batch_code) = :b",
                    {"b": batch_input}
                )
                if not prod.empty:
                    st.success(f"Found: {prod.iloc[0]['product_name']}")
                    st.dataframe(prod[["batch_code", "production_date", "pack_date", "use_by_date",
                                       "raw_input_kg", "finished_output_kg", "yield_pct", "operator", "shift"]],
                                 use_container_width=True)

                    # Linked orders
                    orders = query(
                        "SELECT o.customer, o.quantity_kg, o.order_date, o.delivery_date, o.status "
                        "FROM orders o WHERE UPPER(o.production_batch) = :b",
                        {"b": batch_input}
                    )
                    if not orders.empty:
                        st.markdown("**Linked Orders**")
                        st.dataframe(orders, use_container_width=True)
                else:
                    st.error(f"Batch {batch_input} not found")

    with col2:
        st.markdown("**Recent Production**")
        recent = query("""
            SELECT b.batch_code, b.production_date, p.name, b.finished_output_kg, b.yield_pct
            FROM batches b JOIN products p ON b.product_id = p.id
            ORDER BY b.production_date DESC, b.id DESC LIMIT 15
        """)
        if not recent.empty:
            st.dataframe(recent, use_container_width=True,
                        column_config={"yield_pct": st.column_config.ProgressColumn("Yield %", min_value=0, max_value=100)})

# === TEMPERATURE ===
with tab2:
    st.markdown("### Temperature Monitoring")

    # Current readings
    latest = query("""
        SELECT t1.location, t1.temperature, t1.timestamp, t1.is_excursion
        FROM temperature_logs t1
        INNER JOIN (SELECT location, MAX(timestamp) as max_t FROM temperature_logs GROUP BY location) t2
        ON t1.location = t2.location AND t1.timestamp = t2.max_t
        ORDER BY t1.location
    """)

    if not latest.empty:
        cols = st.columns(len(latest))
        thresholds = config["temperature"]["locations"]
        for i, (_, row) in enumerate(latest.iterrows()):
            loc = row["location"]
            temp = row["temperature"]
            limits = thresholds.get(loc, {"min": -999, "max": 999})
            ok = limits["min"] <= temp <= limits["max"]
            with cols[i]:
                st.metric(loc, f"{temp:.1f}C", delta="OK" if ok else "ALERT",
                         delta_color="normal" if ok else "inverse")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Excursions (7 days)**")
        excursions = query("""
            SELECT location, temperature, timestamp, recorded_by
            FROM temperature_logs
            WHERE is_excursion = 1 AND timestamp >= date('now', '-7 days')
            ORDER BY timestamp DESC
        """)
        if excursions.empty:
            st.success("No excursions in the last 7 days")
        else:
            st.warning(f"{len(excursions)} excursion(s) detected")
            st.dataframe(excursions, use_container_width=True)

    with col2:
        st.markdown("**Trend**")
        locations = list(config["temperature"]["locations"].keys())
        sel_loc = st.selectbox("Location", locations)
        trend = query(
            "SELECT temperature, timestamp FROM temperature_logs "
            "WHERE location = :loc AND timestamp >= date('now', '-7 days') ORDER BY timestamp",
            {"loc": sel_loc}
        )
        if not trend.empty:
            limits = config["temperature"]["locations"][sel_loc]
            fig = px.line(trend, x="timestamp", y="temperature")
            fig.add_hline(y=limits["max"], line_dash="dash", line_color="red", annotation_text=f"Max {limits['max']}C")
            fig.add_hline(y=limits["min"], line_dash="dash", line_color="blue", annotation_text=f"Min {limits['min']}C")
            fig.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0), showlegend=False,
                             xaxis_title="", yaxis_title="Temperature (C)")
            st.plotly_chart(fig, use_container_width=True)

# === ALLERGENS ===
with tab3:
    st.markdown("### Allergen Matrix")
    st.caption("Product x allergen cross-reference. BRC Section 5.")

    products_df = query("SELECT name, species, category, allergens FROM products ORDER BY name")
    if not products_df.empty:
        all_allergens = set()
        for _, row in products_df.iterrows():
            if row["allergens"]:
                for a in str(row["allergens"]).split(","):
                    all_allergens.add(a.strip())
        all_allergens = sorted(all_allergens)

        matrix = []
        for _, row in products_df.iterrows():
            entry = {"Product": row["name"], "Category": row["category"]}
            prod_allergens = [a.strip() for a in str(row["allergens"]).split(",")]
            for a in all_allergens:
                entry[a] = "Y" if a in prod_allergens else ""
            matrix.append(entry)

        matrix_df = pd.DataFrame(matrix)

        # Summary
        cols = st.columns(min(len(all_allergens), 6))
        for i, a in enumerate(all_allergens[:6]):
            count = sum(1 for m in matrix if m.get(a) == "Y")
            with cols[i]:
                st.metric(a, f"{count} products")

        st.divider()

        # Filter
        cats = ["All"] + sorted(products_df["category"].unique().tolist())
        sel_cat = st.selectbox("Category", cats)
        display = matrix_df if sel_cat == "All" else matrix_df[matrix_df["Category"] == sel_cat]

        def highlight(val):
            return "background-color: #fee2e2; color: #991b1b; font-weight: bold" if val == "Y" else ""

        styled = display.style.map(highlight, subset=[c for c in display.columns if c not in ["Product", "Category"]])
        st.dataframe(styled, use_container_width=True, height=400)

        csv = display.to_csv(index=False)
        st.download_button("Export CSV", csv, "allergen_matrix.csv", "text/csv")

# === SHELF LIFE ===
with tab4:
    st.markdown("### Shelf Life & Concessions")
    st.caption("Fresh = +19 days (Superchill). Defrost = +11 days (Chiller). Beyond = concession required.")

    sl_total = scalar("SELECT COUNT(*) FROM batches WHERE production_date >= date('now', '-30 days')") or 0
    sl_conc = scalar("SELECT COUNT(*) FROM batches WHERE production_date >= date('now', '-30 days') AND concession_required = 1") or 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Batches (30d)", sl_total)
    col2.metric("Concessions", sl_conc, delta="OK" if sl_conc == 0 else f"{sl_conc} needed",
                delta_color="normal" if sl_conc == 0 else "inverse")
    col3.metric("Compliance", f"{round(((sl_total - sl_conc) / sl_total) * 100, 1) if sl_total > 0 else 100}%")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Expiring Within 3 Days**")
        expiring = query("""
            SELECT b.batch_code, b.use_by_date, p.name,
                   CAST(julianday(b.use_by_date) - julianday('now') AS INTEGER) as days_left
            FROM batches b JOIN products p ON b.product_id = p.id
            WHERE b.use_by_date >= date('now') AND b.use_by_date <= date('now', '+3 days')
            ORDER BY b.use_by_date
        """)
        if expiring.empty:
            st.success("Nothing expiring in 3 days")
        else:
            st.warning(f"{len(expiring)} batch(es) expiring soon")
            st.dataframe(expiring, use_container_width=True)

    with col2:
        st.markdown("**Concessions (30 days)**")
        concessions = query("""
            SELECT b.batch_code, b.concession_reason, b.pack_date, b.use_by_date, p.name
            FROM batches b JOIN products p ON b.product_id = p.id
            WHERE b.concession_required = 1 AND b.production_date >= date('now', '-30 days')
            ORDER BY b.production_date DESC
        """)
        if concessions.empty:
            st.success("No concessions needed")
        else:
            st.dataframe(concessions, use_container_width=True)

# === AUDIT ===
with tab5:
    st.markdown("### Audit Report")
    st.caption(f"Generate {config['facility']['standard']} compliance report")

    if st.button("Generate Report", type="primary"):
        status = "PASS" if overall >= 85 else "FAIL"
        st.markdown(f"### Status: {'🟢' if status == 'PASS' else '🔴'} {status}")

        col1, col2, col3 = st.columns(3)
        col1.metric("Temperature", f"{temp_score}%")
        col2.metric("Traceability", f"{trace_score}%")
        col3.metric("Overall", f"{overall}%")

        st.divider()

        st.markdown("**Excursions (30 days)**")
        exc_30 = query("SELECT location, temperature, timestamp FROM temperature_logs WHERE is_excursion = 1 AND timestamp >= date('now', '-30 days') ORDER BY timestamp DESC")
        if exc_30.empty:
            st.success("No excursions")
        else:
            st.dataframe(exc_30, use_container_width=True)

        st.markdown("**Allergen Matrix**")
        st.dataframe(matrix_df if 'matrix_df' in dir() else pd.DataFrame(), use_container_width=True)

        # Export
        report = {
            "facility": FACILITY,
            "generated": datetime.now().isoformat(),
            "temperature_score": temp_score,
            "traceability_score": trace_score,
            "overall": overall,
            "status": status,
            "excursions_30d": len(exc_30) if not exc_30.empty else 0,
        }
        st.download_button("Download JSON", json.dumps(report, indent=2), "audit_report.json", "application/json")

        try:
            from modules.report_generator import generate_full_audit_report
            pdf = generate_full_audit_report(
                factory_name=FACILITY, temp_score=temp_score, trace_score=trace_score,
                excursions_df=exc_30,
                allergen_df=matrix_df if 'matrix_df' in dir() else pd.DataFrame(),
                shelf_life_summary={"total_batches": sl_total, "within_spec": sl_total - sl_conc, "concessions": sl_conc,
                                     "compliance_pct": round(((sl_total - sl_conc) / sl_total) * 100, 1) if sl_total > 0 else 100},
                concessions_df=concessions if 'concessions' in dir() else pd.DataFrame(),
                recent_batches_df=recent if 'recent' in dir() else pd.DataFrame(),
            )
            st.download_button("Download PDF Report", data=pdf,
                              file_name=f"brc_audit_{datetime.now().strftime('%Y%m%d')}.pdf",
                              mime="application/pdf")
        except ImportError:
            st.info("PDF export requires fpdf2: pip install fpdf2")
