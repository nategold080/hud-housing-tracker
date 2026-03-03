"""HUD Affordable Housing Compliance Tracker — Streamlit Dashboard."""

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB_PATH = Path(__file__).parent.parent.parent / "data" / "hud_housing.db"


@st.cache_resource
def get_conn():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@st.cache_data(ttl=3600)
def load_table(table: str) -> pd.DataFrame:
    conn = get_conn()
    return pd.read_sql_query(f"SELECT * FROM {table}", conn)


@st.cache_data(ttl=3600)
def load_stats() -> dict:
    conn = get_conn()
    from src.storage.database import get_stats
    return get_stats(conn)


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
    "[LinkedIn](https://linkedin.com/in/nathanmauricegoldberg)"
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

    # KPI cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("LIHTC Projects", f"{stats['lihtc_projects']:,}")
    c2.metric("REAC Inspections", f"{stats['reac_inspections']:,}")
    c3.metric("Multifamily Properties", f"{stats['multifamily_properties']:,}")
    c4.metric("Cross-Links", f"{stats['cross_links']:,}")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Management Companies", f"{stats['owners']:,}")
    c6.metric("Avg Inspection Score", f"{stats['avg_inspection_score']}")
    c7.metric("Failing Inspections", f"{stats['failing_inspections']:,}")
    c8.metric("Total LIHTC Units", f"{stats['total_lihtc_units']:,}")

    st.markdown("---")

    # LIHTC projects by state
    lihtc = load_table("lihtc_projects")
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


# ========================
# Section 2: LIHTC Projects
# ========================
elif section == "LIHTC Projects":
    st.title("LIHTC Tax Credit Projects")
    st.markdown(f"**{stats['lihtc_projects']:,}** projects across **{stats['lihtc_states']}** states/territories")

    lihtc = load_table("lihtc_projects")

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
    st.dataframe(
        filtered[display_cols].sort_values("total_units", ascending=False).head(500),
        use_container_width=True,
        height=400,
    )


# ========================
# Section 3: REAC Inspections
# ========================
elif section == "REAC Inspections":
    st.title("REAC Physical Inspections")
    st.markdown(
        f"**{stats['reac_inspections']:,}** inspections | "
        f"Avg Score: **{stats['avg_inspection_score']}** | "
        f"Failing: **{stats['failing_inspections']:,}**"
    )

    reac = load_table("reac_inspections")

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
    st.dataframe(
        filtered[display_cols].sort_values("inspection_score").head(200),
        use_container_width=True,
        height=400,
    )


# ========================
# Section 4: Management Companies
# ========================
elif section == "Management Companies":
    st.title("Management Company Profiles")
    st.markdown(f"**{stats['owners']:,}** management companies tracked across all data sources")

    owners = load_table("owners")

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
    st.dataframe(
        filtered[display_cols].sort_values("property_count", ascending=False).head(500),
        use_container_width=True,
        height=400,
    )


# ========================
# Section 5: Geographic Analysis
# ========================
elif section == "Geographic Analysis":
    st.title("Geographic Analysis")

    tab1, tab2 = st.tabs(["LIHTC Map", "REAC Scores Map"])

    with tab1:
        st.subheader("LIHTC Projects by Location")
        lihtc = load_table("lihtc_projects")
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
        st.map(sample[["latitude", "longitude"]].rename(columns={"latitude": "lat", "longitude": "lon"}))

    with tab2:
        st.subheader("REAC Inspection Scores by State")
        reac = load_table("reac_inspections")
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
    st.markdown(
        f"**{stats['cross_links']:,}** cross-links connecting LIHTC projects, "
        "multifamily properties, and REAC inspections"
    )

    links = load_table("cross_links")

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


# ========================
# Section 7: Failing Properties
# ========================
elif section == "Failing Properties":
    st.title("Failing Properties (REAC Score < 60)")

    reac = load_table("reac_inspections")
    failing = reac[reac["inspection_score"].notna() & (reac["inspection_score"] < 60)].copy()
    failing = failing.sort_values("inspection_score")

    st.markdown(f"**{len(failing):,}** properties with REAC scores below 60")

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
    owners = load_table("owners")

    # Join failing inspections with multifamily to get mgmt company
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
    st.dataframe(failing[display_cols], use_container_width=True, height=400)


# ========================
# Section 8: Data Explorer
# ========================
elif section == "Data Explorer":
    st.title("Data Explorer")
    st.markdown("Query and explore the raw data tables.")

    table_choice = st.selectbox(
        "Table",
        ["lihtc_projects", "reac_inspections", "multifamily_properties",
         "cross_links", "owners", "section8_contracts"],
    )

    df = load_table(table_choice)
    st.metric("Total Records", f"{len(df):,}")

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
