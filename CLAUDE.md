# HUD Affordable Housing Compliance Tracker

## Project Overview
Cross-linked database connecting LIHTC tax credit projects, REAC physical inspections, and HUD multifamily properties with management company accountability profiles. First dataset to bridge HUD's fragmented data systems into a unified, queryable format.

## Architecture

### Data Sources (3 active)
1. **LIHTC Database** — huduser.gov ZIP/CSV, 54,102 projects
2. **Multifamily Assisted** — ArcGIS FeatureServer, 23,788 properties + embedded REAC scores
3. **Multifamily Insured** — ArcGIS FeatureServer, 17,484 properties + embedded REAC scores

### Database Schema (SQLite, WAL mode)
- `lihtc_projects` — 54,102 records, PK: hud_id
- `reac_inspections` — 33,772 records, PK: inspection_id (extracted from multifamily data)
- `multifamily_properties` — 36,274 records, PK: property_id
- `section8_contracts` — 0 records (future enhancement)
- `cross_links` — 51,427 records (auto-incremented)
- `owners` — 4,556 management company profiles

### Cross-Linking Strategy (5 stages)
1. Property ID match (multifamily → REAC) — confidence 1.0
2. Address match (LIHTC → multifamily) — exact (0.90) + fuzzy ≥85% via rapidfuzz
3. Contract number match (LIHTC → Section 8) — confidence 1.0
4. Address match (LIHTC → REAC) — confidence 0.85
5. Owner/management profile aggregation across all sources

### Key Technical Notes
- REAC scores are NOT standalone — they're embedded fields in multifamily ArcGIS data
- `CLIENT_GROUP_NAME` in multifamily data is tenant category (Elderly, Family), NOT owner
- `MGMT_AGENT_ORG_NAME` is the actual management company → maps to `owner_name`
- LIHTC CSV has empty owner fields — management company data comes from multifamily
- ArcGIS pagination: max 2,000 records/page via resultOffset/resultRecordCount
- REAC scores may have letter suffixes (e.g., "85a") — strip before numeric conversion
- Epoch timestamps in ArcGIS: divide by 1000 for seconds

## CLI Commands
```bash
python -m src.cli download --source all    # Download raw data
python -m src.cli pipeline                 # Full ETL pipeline
python -m src.cli stats                    # Show database stats
python -m src.cli export --format all      # Generate exports
python -m src.cli dashboard               # Launch Streamlit dashboard
```

## File Layout
```
src/
  cli.py                         — Click CLI
  scrapers/lihtc.py              — LIHTC ZIP/CSV download + parse
  scrapers/multifamily.py        — ArcGIS pagination + REAC extraction
  normalization/addresses.py     — Address/owner normalization
  normalization/cross_linker.py  — 5-stage cross-linking engine
  validation/quality.py          — Quality scoring (0.0–1.0)
  storage/database.py            — SQLite schema + CRUD
  export/exporter.py             — CSV/JSON/Excel/Markdown exports
  dashboard/app.py               — 8-section Streamlit dashboard
```

## Testing
106 tests across 8 test files. Run: `python -m pytest tests/ -q`
