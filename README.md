# HUD Affordable Housing Compliance Tracker

The first cross-linked database connecting **LIHTC tax credit projects**, **REAC physical inspections**, and **HUD multifamily properties** with management company accountability profiles.

## Key Numbers

| Metric | Value |
|--------|-------|
| LIHTC Projects | 54,102 |
| REAC Inspections | 33,772 |
| Multifamily Properties | 36,274 |
| Entity Cross-Links | 51,427 |
| Management Companies | 4,556 |
| States/Territories | 56 |
| Total Housing Units | 3.7M+ |
| Failing Properties (REAC <60) | 956 |

## What Makes This Unique

No existing public dataset connects LIHTC allocations to REAC inspection outcomes at the management company level. This tracker:

- **Cross-links** three separate HUD data systems using address matching and property ID resolution
- **Profiles** 4,556 management companies with portfolio-level REAC inspection statistics
- **Identifies** 956 failing properties and links them to responsible management entities
- **Covers** every LIHTC project placed in service from 1987–2023

## Data Sources

1. **LIHTC Database** (HUD User) — 54,102 projects
2. **Multifamily Assisted Properties** (HUD ArcGIS) — 23,788 properties with embedded REAC scores
3. **HUD Insured Multifamily Properties** (HUD ArcGIS) — 17,484 properties with embedded REAC scores

## Quick Start

```bash
pip install -r requirements.txt

# Download data
python -m src.cli download --source all

# Run full pipeline
python -m src.cli pipeline

# View stats
python -m src.cli stats

# Generate exports
python -m src.cli export --format all

# Launch dashboard
streamlit run src/dashboard/app.py
```

## Dashboard

8-section interactive Streamlit dashboard:

1. **Overview** — KPI cards, LIHTC state distribution, REAC score histogram, allocation timeline
2. **LIHTC Projects** — Filterable project explorer with credit type distribution
3. **REAC Inspections** — Inspection analysis with state-level scoring
4. **Management Companies** — Portfolio size vs. inspection quality analysis
5. **Geographic Analysis** — Choropleth maps of LIHTC projects and REAC scores
6. **Cross-Links** — Entity link method and confidence visualization
7. **Failing Properties** — Properties scoring below 60 with management company attribution
8. **Data Explorer** — Raw table browsing with search and CSV download

## Tests

```bash
python -m pytest tests/ -q
# 106 passed
```

## Contact

Built by **Nathan Goldberg**
- Email: nathanmauricegoldberg@gmail.com
- LinkedIn: [linkedin.com/in/nathanmauricegoldberg](https://linkedin.com/in/nathanmauricegoldberg)
