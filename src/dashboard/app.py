"""HUD Affordable Housing Compliance Tracker — Streamlit Dashboard."""

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB_PATH = Path(__file__).parent.parent.parent / "data" / "hud_housing.db"


def _table_exists(conn, name):
    try:
        r = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
        return r is not None
    except Exception:
        return False


def _safe_query(sql, conn, params=()):
    try:
        return pd.read_sql_query(sql, conn, params=params if params else None)
    except Exception:
        return pd.DataFrame()


def _safe_fetchone(conn, sql, params=(), default=0):
    try:
        row = conn.execute(sql, params).fetchone()
        return row[0] if row else default
    except Exception:
        return default


@st.cache_resource
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@st.cache_data(ttl=3600)
def load_table(table: str) -> pd.DataFrame:
    try:
        conn = get_conn()
        return pd.read_sql_query(f"SELECT * FROM [{table}]", conn)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_stats() -> dict:
    conn = get_conn()
    stats = {}
    for table in ["lihtc_projects", "multifamily_properties", "reac_inspections",
                   "section8_contracts", "cross_links", "owners",
                   "hud_enforcement", "fair_market_rent", "property_affordability"]:
        try:
            row = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()
            stats[table] = row[0] if row else 0
        except Exception:
            stats[table] = 0

    # Derived stats
    stats["lihtc_states"] = _safe_fetchone(conn, "SELECT COUNT(DISTINCT state) FROM lihtc_projects", default=0)
    stats["total_lihtc_units"] = _safe_fetchone(conn, "SELECT COALESCE(SUM(total_units), 0) FROM lihtc_projects", default=0)
    stats["avg_inspection_score"] = _safe_fetchone(conn, "SELECT ROUND(AVG(inspection_score), 1) FROM reac_inspections WHERE inspection_score IS NOT NULL AND inspection_score > 0", default=0)
    stats["failing_inspections"] = _safe_fetchone(conn, "SELECT COUNT(*) FROM reac_inspections WHERE inspection_score IS NOT NULL AND inspection_score < 60", default=0)
    stats["expiring_contracts"] = _safe_fetchone(conn, "SELECT COUNT(*) FROM section8_contracts WHERE is_expiring_soon = 1", default=0)
    stats["total_assisted_units"] = _safe_fetchone(conn, "SELECT COALESCE(SUM(assisted_units), 0) FROM section8_contracts", default=0)
    stats["fmr_counties"] = _safe_fetchone(conn, "SELECT COUNT(DISTINCT fips_county) FROM fair_market_rent", default=0)
    stats["avg_rent_fmr_ratio"] = _safe_fetchone(conn, "SELECT ROUND(AVG(rent_to_fmr_ratio), 2) FROM property_affordability WHERE rent_to_fmr_ratio IS NOT NULL", default=0)

    return stats


# --- Page config ---
st.set_page_config(
    page_title="HUD Affordable Housing Tracker",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Sidebar ---
st.sidebar.title("HUD Affordable Housing Tracker")
st.sidebar.markdown("---")

section = st.sidebar.radio(
    "Navigate",
    [
        "Overview",
        "LIHTC Projects",
        "REAC Inspections",
        "Section 8 Contracts",
        "Expiration Risk",
        "Affordability Analysis",
        "Tenant Demographics",
        "Enforcement & Accountability",
        "Management Companies",
        "Geographic Analysis",
        "Cross-Links",
        "Failing Properties",
        "Data Explorer",
    ],
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "Built by **Nathan Goldberg**  \n"
    "[Email](mailto:nathanmauricegoldberg@gmail.com) · "
    "[LinkedIn](https://www.linkedin.com/in/nathan-goldberg-62a44522a/)"
)

# --- Load data ---
stats = load_stats()


# ========================
# Section 1: Overview
# ========================
if section == "Overview":
    st.title("HUD Affordable Housing Compliance Tracker")
    st.markdown(
        "The first cross-linked database connecting **LIHTC tax credit projects**, "
        "**REAC physical inspections**, and **HUD multifamily properties** with "
        "management company accountability tracking."
    )

    conn = get_conn()
    if not _table_exists(conn, "lihtc_projects"):
        st.warning("No data loaded. Run the pipeline first: `python -m src.cli pipeline`")
    else:
        # KPI cards
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("LIHTC Projects", f"{stats.get('lihtc_projects', 0):,}")
        c2.metric("REAC Inspections", f"{stats.get('reac_inspections', 0):,}")
        c3.metric("Multifamily Properties", f"{stats.get('multifamily_properties', 0):,}")
        c4.metric("Cross-Links", f"{stats.get('cross_links', 0):,}")

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Section 8 Contracts", f"{stats.get('section8_contracts', 0):,}")
        c6.metric("Expiring Soon", f"{stats.get('expiring_contracts', 0):,}")
        c7.metric("Management Companies", f"{stats.get('owners', 0):,}")
        c8.metric("Cross-Links", f"{stats.get('cross_links', 0):,}")

        c9, c10, c11, c12 = st.columns(4)
        c9.metric("Avg Inspection Score", f"{stats.get('avg_inspection_score', 0)}")
        c10.metric("Failing Inspections", f"{stats.get('failing_inspections', 0):,}")
        c11.metric("Total LIHTC Units", f"{stats.get('total_lihtc_units', 0):,}")
        c12.metric("Assisted Units (S8)", f"{stats.get('total_assisted_units', 0):,}")

        st.markdown("---")

    # LIHTC projects by state
    lihtc = load_table("lihtc_projects")
    if not lihtc.empty:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("LIHTC Projects by State (Top 20)")
            state_counts = (
                lihtc.groupby("state")
                .agg(projects=("hud_id", "count"), units=("total_units", "sum"))
                .sort_values("projects", ascending=False)
                .head(20)
                .reset_index()
            )
            fig = px.bar(
                state_counts,
                x="state",
                y="projects",
                hover_data=["units"],
                color="projects",
                color_continuous_scale="Blues",
            )
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("REAC Score Distribution")
            reac = load_table("reac_inspections")
            if not reac.empty:
                reac_valid = reac[reac["inspection_score"].notna() & (reac["inspection_score"] > 0)]
                fig2 = px.histogram(
                    reac_valid,
                    x="inspection_score",
                    nbins=50,
                    color_discrete_sequence=["#0984E3"],
                )
                fig2.add_vline(x=60, line_dash="dash", line_color="red", annotation_text="Failing (<60)")
                fig2.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis_title="Inspection Score",
                    yaxis_title="Count",
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No REAC inspection data available.")

        # LIHTC allocation timeline
        st.subheader("LIHTC Allocations Over Time")
        alloc = lihtc[lihtc["allocation_year"].notna() & (lihtc["allocation_year"] > 1986)]
        year_counts = (
            alloc.groupby("allocation_year")
            .agg(projects=("hud_id", "count"), units=("total_units", "sum"))
            .reset_index()
        )
        fig3 = px.area(
            year_counts,
            x="allocation_year",
            y="units",
            hover_data=["projects"],
            color_discrete_sequence=["#0984E3"],
        )
        fig3.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="Allocation Year",
            yaxis_title="Total Units",
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No LIHTC data available. Run the pipeline first.")


# ========================
# Section 2: LIHTC Projects
# ========================
elif section == "LIHTC Projects":
    st.title("LIHTC Tax Credit Projects")

    lihtc = load_table("lihtc_projects")
    if lihtc.empty:
        st.warning("No LIHTC data loaded. Run the pipeline first: `python -m src.cli pipeline`")
    else:
        st.markdown(f"**{stats.get('lihtc_projects', 0):,}** projects across **{stats.get('lihtc_states', 0)}** states/territories")

        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            states = sorted(lihtc["state"].dropna().unique())
            sel_state = st.selectbox("State", ["All"] + states, key="lihtc_state")
        with col2:
            credit_types = sorted(lihtc["credit_type"].dropna().unique())
            sel_credit = st.selectbox("Credit Type", ["All"] + credit_types)
        with col3:
            min_units = st.number_input("Min Units", 0, 10000, 0)

        filtered = lihtc.copy()
        if sel_state != "All":
            filtered = filtered[filtered["state"] == sel_state]
        if sel_credit != "All":
            filtered = filtered[filtered["credit_type"] == sel_credit]
        if min_units > 0:
            filtered = filtered[filtered["total_units"].fillna(0) >= min_units]

        st.metric("Filtered Projects", f"{len(filtered):,}")

        # Credit type distribution
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Credit Type Distribution")
            ct = filtered["credit_type"].value_counts().reset_index()
            ct.columns = ["credit_type", "count"]
            fig = px.pie(ct, values="count", names="credit_type", color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Units by Allocation Year")
            valid = filtered[filtered["allocation_year"].notna() & (filtered["allocation_year"] > 1986)]
            yr = valid.groupby("allocation_year").agg(units=("total_units", "sum")).reset_index()
            fig2 = px.bar(yr, x="allocation_year", y="units", color_discrete_sequence=["#0984E3"])
            fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)

        # Data table
        st.subheader("Project Records")
        display_cols = ["hud_id", "project_name", "address", "city", "state", "zip_code",
                        "total_units", "li_units", "credit_type", "allocation_year", "placed_in_service_year",
                        "owner", "quality_score"]
        avail_cols = [c for c in display_cols if c in filtered.columns]
        st.dataframe(
            filtered[avail_cols].sort_values("total_units", ascending=False).head(500),
            use_container_width=True,
            height=400,
        )


# ========================
# Section 3: REAC Inspections
# ========================
elif section == "REAC Inspections":
    st.title("REAC Physical Inspections")

    reac = load_table("reac_inspections")
    if reac.empty:
        st.warning("No REAC inspection data loaded. Run the pipeline first: `python -m src.cli pipeline`")
    else:
        st.markdown(
            f"**{stats.get('reac_inspections', 0):,}** inspections | "
            f"Avg Score: **{stats.get('avg_inspection_score', 0)}** | "
            f"Failing: **{stats.get('failing_inspections', 0):,}**"
        )

        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            states = sorted(reac["state"].dropna().unique())
            sel_state = st.selectbox("State", ["All"] + states, key="reac_state")
        with col2:
            max_score = st.slider("Max Score", 0, 100, 100)
        with col3:
            prop_types = sorted(reac["property_type"].dropna().unique())
            sel_type = st.selectbox("Property Type", ["All"] + prop_types)

        filtered = reac.copy()
        if sel_state != "All":
            filtered = filtered[filtered["state"] == sel_state]
        if max_score < 100:
            filtered = filtered[filtered["inspection_score"].fillna(100) <= max_score]
        if sel_type != "All":
            filtered = filtered[filtered["property_type"] == sel_type]

        st.metric("Filtered Inspections", f"{len(filtered):,}")

        # Score by state
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Average Score by State (Top 20)")
            state_scores = (
                filtered.groupby("state")
                .agg(avg_score=("inspection_score", "mean"), count=("inspection_id", "count"))
                .sort_values("count", ascending=False)
                .head(20)
                .reset_index()
            )
            state_scores["avg_score"] = state_scores["avg_score"].round(1)
            fig = px.bar(
                state_scores.sort_values("avg_score"),
                x="avg_score",
                y="state",
                orientation="h",
                color="avg_score",
                color_continuous_scale="RdYlGn",
                hover_data=["count"],
            )
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Score Distribution")
            valid = filtered[filtered["inspection_score"].notna() & (filtered["inspection_score"] > 0)]
            fig2 = px.histogram(valid, x="inspection_score", nbins=40, color_discrete_sequence=["#0984E3"])
            fig2.add_vline(x=60, line_dash="dash", line_color="red", annotation_text="Failing")
            fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)

        # Worst inspections table
        st.subheader("Lowest-Scoring Inspections")
        display_cols = ["inspection_id", "property_name", "address", "city", "state",
                        "inspection_date", "inspection_score", "property_type", "units"]
        avail_cols = [c for c in display_cols if c in filtered.columns]
        st.dataframe(
            filtered[avail_cols].sort_values("inspection_score").head(200),
            use_container_width=True,
            height=400,
        )


# ========================
# Section 4: Section 8 Contracts
# ========================
elif section == "Section 8 Contracts":
    st.title("Section 8 Housing Assistance Contracts")
    st.markdown(
        f"**{stats.get('section8_contracts', 0):,}** contracts | "
        f"**{stats.get('total_assisted_units', 0):,}** assisted units | "
        f"**{stats.get('expiring_contracts', 0):,}** expiring within 3 years"
    )

    sec8 = load_table("section8_contracts")

    if len(sec8) > 0:
        # KPIs
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Contracts", f"{len(sec8):,}")
        c2.metric("With Expiration Date", f"{sec8['contract_end_date'].notna().sum():,}")
        exp_soon = sec8[sec8["is_expiring_soon"] == 1]
        c3.metric("Expiring <3 Years", f"{len(exp_soon):,}")
        c4.metric("Program Types", f"{sec8['program_type'].nunique()}")

        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            states = sorted(sec8["state"].dropna().unique())
            sel_state = st.selectbox("State", ["All"] + list(states), key="sec8_state")
        with col2:
            programs = sorted(sec8["program_type"].dropna().unique())
            sel_prog = st.selectbox("Program Type", ["All"] + list(programs), key="sec8_prog")
        with col3:
            exp_filter = st.selectbox("Expiration Status", ["All", "Expiring Soon", "Not Expiring"], key="sec8_exp")

        filtered = sec8.copy()
        if sel_state != "All":
            filtered = filtered[filtered["state"] == sel_state]
        if sel_prog != "All":
            filtered = filtered[filtered["program_type"] == sel_prog]
        if exp_filter == "Expiring Soon":
            filtered = filtered[filtered["is_expiring_soon"] == 1]
        elif exp_filter == "Not Expiring":
            filtered = filtered[filtered["is_expiring_soon"] != 1]

        st.metric("Filtered Contracts", f"{len(filtered):,}")

        # Charts
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Contracts by Program Type")
            prog_counts = filtered["program_type"].value_counts().head(15).reset_index()
            prog_counts.columns = ["program_type", "count"]
            fig = px.bar(prog_counts, x="program_type", y="count", color="count",
                        color_continuous_scale="Blues")
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Contracts by State (Top 20)")
            state_counts = filtered["state"].value_counts().head(20).reset_index()
            state_counts.columns = ["state", "count"]
            fig2 = px.bar(state_counts, x="state", y="count", color="count",
                         color_continuous_scale="Blues")
            fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

        # Assisted units by state
        st.subheader("Assisted Units by State")
        units_by_state = (
            filtered[filtered["assisted_units"].notna()]
            .groupby("state")
            .agg(total_units=("assisted_units", "sum"), contracts=("contract_id", "count"))
            .sort_values("total_units", ascending=False)
            .head(20)
            .reset_index()
        )
        fig3 = px.bar(units_by_state, x="state", y="total_units", hover_data=["contracts"],
                      color="total_units", color_continuous_scale="Blues")
        fig3.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

        # Data table
        st.subheader("Contract Records")
        display_cols = ["contract_id", "property_name", "address", "city", "state",
                       "program_type", "assisted_units", "contract_end_date",
                       "is_expiring_soon", "days_until_expiration", "owner_name", "rent_per_month"]
        avail_cols = [c for c in display_cols if c in filtered.columns]
        st.dataframe(
            filtered[avail_cols].sort_values("days_until_expiration", na_position="last").head(500),
            use_container_width=True, height=400,
        )
    else:
        st.info("No Section 8 contract data available. Run the pipeline to extract contracts.")


# ========================
# Section 5: Expiration Risk
# ========================
elif section == "Expiration Risk":
    st.title("Section 8 Contract Expiration Risk Analysis")

    sec8 = load_table("section8_contracts")

    if len(sec8) > 0:
        # Filter to contracts with expiration data
        has_exp = sec8[sec8["contract_end_date"].notna() & (sec8["contract_end_date"] != "")].copy()
        has_exp["contract_end_date"] = pd.to_datetime(has_exp["contract_end_date"], errors="coerce")
        has_exp = has_exp[has_exp["contract_end_date"].notna()]

        expiring_1yr = has_exp[has_exp["days_until_expiration"].between(0, 365)]
        expiring_2yr = has_exp[has_exp["days_until_expiration"].between(0, 730)]
        expiring_3yr = has_exp[has_exp["days_until_expiration"].between(0, 1095)]
        already_expired = has_exp[has_exp["days_until_expiration"] < 0] if "days_until_expiration" in has_exp.columns else pd.DataFrame()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Already Expired", f"{len(already_expired):,}")
        c2.metric("Expiring <1 Year", f"{len(expiring_1yr):,}")
        c3.metric("Expiring <2 Years", f"{len(expiring_2yr):,}")
        c4.metric("Expiring <3 Years", f"{len(expiring_3yr):,}")

        # Expiration timeline
        st.subheader("Contract Expiration Timeline")
        has_exp["exp_year"] = has_exp["contract_end_date"].dt.year
        yearly = has_exp.groupby("exp_year").agg(
            contracts=("contract_id", "count"),
            units=("assisted_units", "sum"),
        ).reset_index()
        yearly = yearly[(yearly["exp_year"] >= 2020) & (yearly["exp_year"] <= 2050)]
        fig = px.bar(yearly, x="exp_year", y="contracts", hover_data=["units"],
                    color="contracts", color_continuous_scale="Reds")
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                         plot_bgcolor="rgba(0,0,0,0)", xaxis_title="Expiration Year",
                         yaxis_title="Number of Contracts", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        # Units at risk by year
        st.subheader("Assisted Units at Risk by Expiration Year")
        fig2 = px.bar(yearly, x="exp_year", y="units",
                     color="units", color_continuous_scale="OrRd")
        fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", xaxis_title="Expiration Year",
                          yaxis_title="Assisted Units", showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

        # Geographic risk - expiring by state
        st.subheader("Expiring Contracts by State (Next 3 Years)")
        exp_state = (
            expiring_3yr.groupby("state")
            .agg(contracts=("contract_id", "count"), units=("assisted_units", "sum"))
            .sort_values("contracts", ascending=False)
            .reset_index()
        )
        if len(exp_state) > 0:
            fig3 = px.choropleth(
                exp_state, locations="state", locationmode="USA-states",
                color="contracts", color_continuous_scale="Reds", scope="usa",
                hover_data=["units"],
            )
            fig3.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                geo=dict(bgcolor="rgba(0,0,0,0)"), height=500,
            )
            st.plotly_chart(fig3, use_container_width=True)

        # Management companies with most expiring contracts
        st.subheader("Management Companies with Most Expiring Contracts (3yr)")
        mgmt_exp = (
            expiring_3yr[expiring_3yr["owner_name"].notna() & (expiring_3yr["owner_name"] != "")]
            .groupby("owner_name")
            .agg(expiring=("contract_id", "count"), units_at_risk=("assisted_units", "sum"))
            .sort_values("expiring", ascending=False)
            .head(20)
            .reset_index()
        )
        if len(mgmt_exp) > 0:
            st.dataframe(mgmt_exp, use_container_width=True)

        # Full expiring contracts list
        st.subheader("Contracts Expiring Soon")
        display_cols = ["contract_id", "property_name", "city", "state",
                       "program_type", "assisted_units", "contract_end_date",
                       "days_until_expiration", "owner_name"]
        avail_cols = [c for c in display_cols if c in expiring_3yr.columns]
        st.dataframe(
            expiring_3yr[avail_cols].sort_values("days_until_expiration").head(500),
            use_container_width=True, height=400,
        )
    else:
        st.info("No Section 8 contract data available. Run the pipeline to extract contracts.")


# ========================
# Section 6: Affordability Analysis
# ========================
elif section == "Affordability Analysis":
    st.title("Affordability Analysis — Rent vs. Fair Market Rent")

    # Check if FMR data exists
    fmr_count = stats.get("fair_market_rent", 0)
    afford_count = stats.get("property_affordability", 0)

    if fmr_count > 0:
        st.markdown(
            f"**{fmr_count:,}** county FMR records | "
            f"**{afford_count:,}** properties with affordability analysis | "
            f"**{stats.get('fmr_counties', 0):,}** counties covered"
        )

        if afford_count > 0:
            afford = load_table("property_affordability")

            c1, c2, c3, c4 = st.columns(4)
            below = len(afford[afford["affordability_status"] == "below_fmr"])
            at = len(afford[afford["affordability_status"] == "at_fmr"])
            above = len(afford[afford["affordability_status"] == "above_fmr"])
            c1.metric("Below FMR", f"{below:,}")
            c2.metric("At FMR", f"{at:,}")
            c3.metric("Above FMR", f"{above:,}")
            c4.metric("Avg Rent/FMR Ratio", f"{stats.get('avg_rent_fmr_ratio', 0):.2f}")

            # Status distribution
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Affordability Status Distribution")
                status_counts = afford["affordability_status"].value_counts().reset_index()
                status_counts.columns = ["status", "count"]
                colors = {"below_fmr": "#27ae60", "at_fmr": "#f39c12", "above_fmr": "#e74c3c", "unknown": "#95a5a6"}
                fig = px.pie(status_counts, values="count", names="status",
                            color="status", color_discrete_map=colors)
                fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("Rent-to-FMR Ratio Distribution")
                valid = afford[afford["rent_to_fmr_ratio"].notna()]
                fig2 = px.histogram(valid, x="rent_to_fmr_ratio", nbins=50,
                                   color_discrete_sequence=["#0984E3"])
                fig2.add_vline(x=1.0, line_dash="dash", line_color="red",
                             annotation_text="FMR = 100%")
                fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(0,0,0,0)",
                                  xaxis_title="Rent / FMR Ratio", yaxis_title="Count")
                st.plotly_chart(fig2, use_container_width=True)

            # Data table
            st.subheader("Property Affordability Details")
            st.dataframe(
                afford.sort_values("rent_to_fmr_ratio", ascending=False).head(500),
                use_container_width=True, height=400,
            )
        else:
            st.info("Affordability data not yet computed. Run the pipeline with FMR data.")

        # FMR trends by state
        fmr = load_table("fair_market_rent")
        st.subheader("Fair Market Rent by State (2BR)")
        state_fmr = (
            fmr.groupby("state")
            .agg(avg_fmr_2br=("fmr_2br", "mean"), counties=("fips_county", "nunique"))
            .sort_values("avg_fmr_2br", ascending=False)
            .reset_index()
        )
        state_fmr["avg_fmr_2br"] = state_fmr["avg_fmr_2br"].round(0)
        fig3 = px.choropleth(
            state_fmr, locations="state", locationmode="USA-states",
            color="avg_fmr_2br", color_continuous_scale="YlOrRd", scope="usa",
            hover_data=["counties"],
            labels={"avg_fmr_2br": "Avg 2BR FMR ($)"},
        )
        fig3.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            geo=dict(bgcolor="rgba(0,0,0,0)"), height=500,
        )
        st.plotly_chart(fig3, use_container_width=True)

        # FMR year-over-year trend
        if fmr["fiscal_year"].nunique() > 1:
            st.subheader("FMR Trend Over Time (National Average)")
            year_trend = fmr.groupby("fiscal_year").agg(
                avg_2br=("fmr_2br", "mean"),
                avg_1br=("fmr_1br", "mean"),
                avg_studio=("fmr_studio", "mean"),
            ).reset_index()
            fig4 = px.line(year_trend, x="fiscal_year",
                          y=["avg_studio", "avg_1br", "avg_2br"],
                          labels={"value": "Monthly Rent ($)", "variable": "Bedroom Size"},
                          color_discrete_sequence=["#0984E3", "#00b894", "#e17055"])
            fig4.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No Fair Market Rent data available. Run 'download' then 'pipeline' to add FMR data.")


# ========================
# Section 7: Tenant Demographics
# ========================
elif section == "Tenant Demographics":
    st.title("Tenant Demographics & Occupancy Analysis")

    mf = load_table("multifamily_properties")
    reac = load_table("reac_inspections")

    if mf.empty or "occupancy_type" not in mf.columns:
        has_occ = pd.DataFrame()
    else:
        has_occ = mf[mf["occupancy_type"].notna() & (mf["occupancy_type"] != "")]

    if len(has_occ) > 0:
        st.markdown(f"**{len(has_occ):,}** properties with occupancy type classification")

        # Occupancy type breakdown
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Properties by Occupancy Type")
            occ_counts = has_occ["occupancy_type"].value_counts().reset_index()
            occ_counts.columns = ["occupancy_type", "count"]
            fig = px.pie(occ_counts, values="count", names="occupancy_type",
                        color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Units by Occupancy Type")
            occ_units = (
                has_occ.groupby("occupancy_type")
                .agg(total_units=("total_units", "sum"), properties=("property_id", "count"))
                .sort_values("total_units", ascending=False)
                .reset_index()
            )
            fig2 = px.bar(occ_units, x="occupancy_type", y="total_units",
                         hover_data=["properties"],
                         color="total_units", color_continuous_scale="Blues")
            fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

        # REAC scores by occupancy type
        st.subheader("Average REAC Score by Occupancy Type")
        # Join MF with REAC via property_id
        merged = has_occ.merge(
            reac[["property_id", "inspection_score"]],
            on="property_id", how="inner",
        )
        if len(merged) > 0:
            occ_scores = (
                merged.groupby("occupancy_type")
                .agg(
                    avg_score=("inspection_score", "mean"),
                    count=("property_id", "count"),
                    failing=("inspection_score", lambda x: (x < 60).sum()),
                )
                .sort_values("avg_score")
                .reset_index()
            )
            occ_scores["avg_score"] = occ_scores["avg_score"].round(1)

            fig3 = px.bar(occ_scores, x="occupancy_type", y="avg_score",
                         color="avg_score", color_continuous_scale="RdYlGn",
                         hover_data=["count", "failing"],
                         text="avg_score")
            fig3.add_hline(y=60, line_dash="dash", line_color="red", annotation_text="Failing")
            fig3.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig3, use_container_width=True)

            st.dataframe(occ_scores, use_container_width=True)

        # Occupancy percentage distribution
        has_pct = mf[mf["pct_occupied"].notna() & (mf["pct_occupied"] > 0)]
        if len(has_pct) > 0:
            st.subheader("Occupancy Rate Distribution")
            fig4 = px.histogram(has_pct, x="pct_occupied", nbins=50,
                               color_discrete_sequence=["#0984E3"])
            fig4.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)",
                              xaxis_title="Occupancy %", yaxis_title="Properties")
            st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No occupancy type data available. Run the pipeline to extract tenant demographics.")


# ========================
# Section 8: Enforcement & Accountability
# ========================
elif section == "Enforcement & Accountability":
    st.title("Enforcement & Accountability")

    enforce = load_table("hud_enforcement")

    if len(enforce) > 0:
        st.markdown(
            f"**{len(enforce):,}** enforcement actions tracked — "
            f"troubled designations, high-risk flags, and failing inspections"
        )

        # KPI row
        c1, c2, c3, c4 = st.columns(4)
        troubled = len(enforce[enforce["action_type"] == "troubled_designation"])
        high_risk = len(enforce[enforce["action_type"] == "high_risk_designation"])
        failing = len(enforce[enforce["action_type"] == "failing_inspection"])
        unique_props = enforce["property_id"].nunique()
        c1.metric("Troubled Properties", f"{troubled:,}")
        c2.metric("High-Risk Designations", f"{high_risk:,}")
        c3.metric("Failing Inspections", f"{failing:,}")
        c4.metric("Unique Properties Flagged", f"{unique_props:,}")

        # Chart: action types
        st.subheader("Actions by Type")
        type_counts = enforce["action_type"].value_counts().reset_index()
        type_counts.columns = ["action_type", "count"]
        fig1 = px.bar(type_counts, x="action_type", y="count",
                      color="action_type",
                      color_discrete_sequence=["#E74C3C", "#E67E22", "#F39C12"])
        fig1.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                          xaxis_title="Action Type", yaxis_title="Count")
        st.plotly_chart(fig1, use_container_width=True)

        # Chart: by source
        st.subheader("Actions by Data Source")
        src_counts = enforce["source"].value_counts().reset_index()
        src_counts.columns = ["source", "count"]
        fig2 = px.pie(src_counts, names="source", values="count",
                      color_discrete_sequence=["#0984E3", "#E74C3C", "#2ECC71"])
        fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

        # Cross-reference with multifamily for geographic breakdown
        mf = load_table("multifamily_properties")
        if len(mf) > 0 and "state_code" in mf.columns:
            merged = enforce.merge(
                mf[["property_id", "state_code", "property_name"]],
                on="property_id", how="left"
            )
            state_data = merged.dropna(subset=["state_code"])
            if len(state_data) > 0:
                st.subheader("Enforcement Actions by State")
                state_counts = state_data.groupby("state_code").size().reset_index(name="actions")
                fig3 = px.choropleth(
                    state_counts, locations="state_code", locationmode="USA-states",
                    color="actions", scope="usa",
                    color_continuous_scale="OrRd",
                    labels={"actions": "Enforcement Actions"},
                )
                fig3.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(0,0,0,0)", geo_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig3, use_container_width=True)

        # Resolution status
        st.subheader("Resolution Status")
        status_counts = enforce["resolution_status"].value_counts().reset_index()
        status_counts.columns = ["status", "count"]
        fig4 = px.pie(status_counts, names="status", values="count",
                      color_discrete_sequence=["#E74C3C", "#2ECC71", "#F39C12"])
        fig4.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig4, use_container_width=True)

        # Detail table
        st.subheader("Enforcement Actions Detail")
        show_cols = ["property_id", "action_type", "action_date", "description",
                     "resolution_status", "source", "quality_score"]
        avail_cols = [c for c in show_cols if c in enforce.columns]
        st.dataframe(enforce[avail_cols].head(500), use_container_width=True)
    else:
        st.info("No enforcement data available. Run the pipeline to extract enforcement actions.")


# ========================
# Section 9: Management Companies
# ========================
elif section == "Management Companies":
    st.title("Management Company Profiles")

    try:
        owners = load_table("owners")
        if owners.empty:
            st.warning("No management company data loaded. Run the pipeline first: `python -m src.cli pipeline`")
        else:
            st.markdown(f"**{stats.get('owners', 0):,}** management companies tracked across all data sources")

            # Filters
            col1, col2 = st.columns(2)
            with col1:
                min_props = st.slider("Min Properties Managed", 1, 100, 5)
            with col2:
                search = st.text_input("Search Company Name")

            filtered = owners[owners["property_count"] >= min_props]
            if search:
                filtered = filtered[filtered["normalized_name"].str.contains(search.upper(), na=False)]

            st.metric("Companies Shown", f"{len(filtered):,}")

            # Top companies
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Largest Management Companies")
                top = filtered.nlargest(20, "property_count")
                fig = px.bar(
                    top,
                    x="property_count",
                    y="normalized_name",
                    orientation="h",
                    color="avg_inspection_score",
                    color_continuous_scale="RdYlGn",
                )
                fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    yaxis=dict(autorange="reversed"),
                    height=500,
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("Worst Average Inspection Scores")
                has_score = filtered[filtered["avg_inspection_score"].notna() & (filtered["property_count"] >= 5)]
                worst = has_score.nsmallest(20, "avg_inspection_score")
                fig2 = px.bar(
                    worst,
                    x="avg_inspection_score",
                    y="normalized_name",
                    orientation="h",
                    color="avg_inspection_score",
                    color_continuous_scale="RdYlGn",
                    hover_data=["property_count", "failed_inspections"],
                )
                fig2.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    yaxis=dict(autorange="reversed"),
                    height=500,
                )
                st.plotly_chart(fig2, use_container_width=True)

            # Score vs. portfolio size scatter
            st.subheader("Portfolio Size vs. Inspection Quality")
            scatter_data = filtered[filtered["avg_inspection_score"].notna()].copy()
            fig3 = px.scatter(
                scatter_data,
                x="property_count",
                y="avg_inspection_score",
                size="total_units",
                color="failed_inspections",
                color_continuous_scale="Reds",
                hover_name="normalized_name",
                hover_data=["states_active"],
            )
            fig3.add_hline(y=60, line_dash="dash", line_color="red", annotation_text="Failing Threshold")
            fig3.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis_title="Properties Managed",
                yaxis_title="Avg Inspection Score",
            )
            st.plotly_chart(fig3, use_container_width=True)

            # Data table
            st.subheader("Company Details")
            display_cols = ["normalized_name", "property_count", "total_units",
                            "avg_inspection_score", "min_inspection_score",
                            "failed_inspections", "states_active"]
            avail_cols = [c for c in display_cols if c in filtered.columns]
            st.dataframe(
                filtered[avail_cols].sort_values("property_count", ascending=False).head(500),
                use_container_width=True,
                height=400,
            )
    except Exception as e:
        st.warning(f"Error loading management company data: {e}")


# ========================
# Section 5: Geographic Analysis
# ========================
elif section == "Geographic Analysis":
    st.title("Geographic Analysis")

    tab1, tab2 = st.tabs(["LIHTC Map", "REAC Scores Map"])

    with tab1:
        st.subheader("LIHTC Projects by Location")
        lihtc = load_table("lihtc_projects")
        if lihtc.empty:
            st.info("No LIHTC data available for mapping.")
        else:
            map_data = lihtc[
                lihtc["latitude"].notna() & lihtc["longitude"].notna()
                & (lihtc["latitude"] != 0) & (lihtc["longitude"] != 0)
                & (lihtc["latitude"].between(18, 72)) & (lihtc["longitude"].between(-180, -60))
            ].copy()

            # State-level choropleth
            state_agg = (
                lihtc.groupby("state")
                .agg(projects=("hud_id", "count"), units=("total_units", "sum"))
                .reset_index()
            )
            fig = px.choropleth(
                state_agg,
                locations="state",
                locationmode="USA-states",
                color="projects",
                color_continuous_scale="Blues",
                scope="usa",
                hover_data=["units"],
            )
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                geo=dict(bgcolor="rgba(0,0,0,0)"),
                height=500,
            )
            st.plotly_chart(fig, use_container_width=True)

            # Point map (sampled for performance)
            if len(map_data) > 5000:
                sample = map_data.sample(5000, random_state=42)
            else:
                sample = map_data
            if not sample.empty:
                st.map(sample[["latitude", "longitude"]].rename(columns={"latitude": "lat", "longitude": "lon"}))

    with tab2:
        st.subheader("REAC Inspection Scores by State")
        reac = load_table("reac_inspections")
        if reac.empty:
            st.info("No REAC data available for mapping.")
        else:
            state_scores = (
                reac[reac["inspection_score"].notna()]
                .groupby("state")
                .agg(
                    avg_score=("inspection_score", "mean"),
                    failing=("inspection_score", lambda x: (x < 60).sum()),
                    count=("inspection_id", "count"),
                )
                .reset_index()
            )
            state_scores["avg_score"] = state_scores["avg_score"].round(1)

            fig2 = px.choropleth(
                state_scores,
                locations="state",
                locationmode="USA-states",
                color="avg_score",
                color_continuous_scale="RdYlGn",
                scope="usa",
                hover_data=["count", "failing"],
            )
            fig2.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                geo=dict(bgcolor="rgba(0,0,0,0)"),
                height=500,
            )
            st.plotly_chart(fig2, use_container_width=True)


# ========================
# Section 6: Cross-Links
# ========================
elif section == "Cross-Links":
    st.title("Entity Cross-Links")

    links = load_table("cross_links")
    if links.empty:
        st.warning("No cross-link data loaded. Run the pipeline first: `python -m src.cli pipeline`")
    else:
        st.markdown(
            f"**{stats.get('cross_links', 0):,}** cross-links connecting LIHTC projects, "
            "multifamily properties, and REAC inspections"
        )

        try:
            # Link method breakdown
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Links by Method")
                method_counts = links["link_method"].value_counts().reset_index()
                method_counts.columns = ["method", "count"]
                fig = px.pie(method_counts, values="count", names="method", color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("Links by Type")
                type_counts = links.groupby(["source_type", "target_type"]).size().reset_index(name="count")
                type_counts["pair"] = type_counts["source_type"] + " → " + type_counts["target_type"]
                fig2 = px.bar(type_counts, x="pair", y="count", color="pair", color_discrete_sequence=px.colors.qualitative.Set2)
                fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)

            # Confidence distribution
            st.subheader("Link Confidence Distribution")
            fig3 = px.histogram(links, x="confidence", nbins=20, color_discrete_sequence=["#0984E3"])
            fig3.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig3, use_container_width=True)

            # Sample links
            st.subheader("Sample Cross-Links")
            st.dataframe(links.head(200), use_container_width=True, height=400)
        except Exception as e:
            st.warning(f"Error rendering cross-link data: {e}")


# ========================
# Section 7: Failing Properties
# ========================
elif section == "Failing Properties":
    st.title("Failing Properties (REAC Score < 60)")

    reac = load_table("reac_inspections")
    if reac.empty:
        st.warning("No REAC data loaded. Run the pipeline first: `python -m src.cli pipeline`")
        failing = pd.DataFrame()
    else:
        failing = reac[reac["inspection_score"].notna() & (reac["inspection_score"] < 60)].copy()
        failing = failing.sort_values("inspection_score")

    if not failing.empty:
        st.markdown(f"**{len(failing):,}** properties with REAC scores below 60")

        try:
            # State breakdown
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Failing Properties by State")
                state_fail = failing["state"].value_counts().head(20).reset_index()
                state_fail.columns = ["state", "count"]
                fig = px.bar(state_fail, x="state", y="count", color="count", color_continuous_scale="Reds")
                fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("Score Distribution (Failing)")
                fig2 = px.histogram(failing, x="inspection_score", nbins=30, color_discrete_sequence=["#e74c3c"])
                fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)

            # Cross-reference with management companies
            mf = load_table("multifamily_properties")
            if not mf.empty and "property_id" in mf.columns and "owner_name" in mf.columns:
                failing_props = failing.merge(
                    mf[["property_id", "owner_name"]],
                    on="property_id",
                    how="left",
                )

                mgmt_fail = (
                    failing_props[failing_props["owner_name"].notna() & (failing_props["owner_name"] != "")]
                    .groupby("owner_name")
                    .agg(
                        failing_count=("inspection_id", "count"),
                        avg_fail_score=("inspection_score", "mean"),
                        worst_score=("inspection_score", "min"),
                    )
                    .sort_values("failing_count", ascending=False)
                    .head(20)
                    .reset_index()
                )
                mgmt_fail["avg_fail_score"] = mgmt_fail["avg_fail_score"].round(1)

                if len(mgmt_fail) > 0:
                    st.subheader("Management Companies with Most Failing Properties")
                    st.dataframe(mgmt_fail, use_container_width=True)

            # Full failing list
            st.subheader("All Failing Properties")
            display_cols = ["inspection_id", "property_name", "address", "city", "state",
                            "inspection_date", "inspection_score", "property_type", "units"]
            avail_cols = [c for c in display_cols if c in failing.columns]
            st.dataframe(failing[avail_cols], use_container_width=True, height=400)
        except Exception as e:
            st.warning(f"Error rendering failing properties: {e}")


# ========================
# Section 8: Data Explorer
# ========================
elif section == "Data Explorer":
    st.title("Data Explorer")
    st.markdown("Query and explore the raw data tables.")

    table_choice = st.selectbox(
        "Table",
        ["lihtc_projects", "reac_inspections", "multifamily_properties",
         "section8_contracts", "cross_links", "owners",
         "hud_enforcement", "fair_market_rent", "property_affordability"],
    )

    df = load_table(table_choice)
    st.metric("Total Records", f"{len(df):,}")

    if df.empty:
        st.info(f"No data in table `{table_choice}`. Run the pipeline to load data.")
    else:
        # Column filter
        cols = list(df.columns)
        sel_cols = st.multiselect("Columns", cols, default=cols[:10])

        # Search
        search = st.text_input("Search (filters all text columns)")
        if search:
            mask = df.apply(lambda row: row.astype(str).str.contains(search, case=False, na=False).any(), axis=1)
            df = df[mask]
            st.info(f"Found {len(df):,} matching records")

        if sel_cols:
            st.dataframe(df[sel_cols].head(1000), use_container_width=True, height=500)

        # Download
        csv_data = df.to_csv(index=False)
        st.download_button(
            "Download CSV",
            csv_data,
            file_name=f"{table_choice}.csv",
            mime="text/csv",
        )
