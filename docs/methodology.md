# HUD Affordable Housing Compliance Tracker — Methodology

## Overview

This tracker is the first cross-linked database connecting LIHTC tax credit projects, REAC physical inspections, and HUD multifamily assisted/insured properties with management company accountability profiles. It enables analysis of affordable housing quality patterns at the management company level — something not previously possible with any single HUD dataset.

## Data Sources

### 1. LIHTC Database (HUD User)
- **URL:** https://www.huduser.gov/lihtc/lihtcpub.zip
- **Records:** 54,102 projects
- **Coverage:** All LIHTC projects placed in service 1987–2023, all 50 states + territories
- **Fields used:** HUD_ID, project name, address, city, state, ZIP, total units, low-income units, credit type (4%/9%), placed-in-service year, allocation year, owner, management company
- **Update frequency:** Annual

### 2. Multifamily Assisted Properties (HUD ArcGIS)
- **URL:** ArcGIS FeatureServer (Multifamily_Properties_Assisted)
- **Records:** 23,788 properties
- **Coverage:** All HUD-assisted multifamily properties with active assistance contracts
- **Fields used:** Property ID, name, address, management agent, program type, total/assisted units, Section 8/202/811 indicators, REAC last inspection score/date/ID, occupancy rate, risk category
- **Update frequency:** Monthly

### 3. HUD Insured Multifamily Properties (HUD ArcGIS)
- **URL:** ArcGIS FeatureServer (HUD_Insured_Multifamily_Properties)
- **Records:** 17,484 properties
- **Coverage:** All FHA-insured multifamily properties
- **Fields used:** Property ID, name, address, management agent, total/contract units, Section 8/202/811 indicators, REAC score, financing type, loan amount
- **Update frequency:** Monthly

### 4. REAC Inspections (Extracted from Multifamily Data)
- **Records:** 33,772 inspections
- **Source:** Embedded in Multifamily Assisted and Insured datasets
- **Fields used:** Inspection ID, property ID, date, score (0-100), property type
- **Note:** REAC scores embedded in multifamily data represent the most recent inspection only

## Data Processing Pipeline

### Step 1: Download and Cache
Raw data is downloaded and cached locally to minimize API calls. LIHTC data arrives as a ZIP archive containing CSV. Multifamily data is paginated from ArcGIS FeatureServer (2,000 records per page).

### Step 2: Parse and Normalize
- **Address normalization:** Street type standardization (St→ST, Avenue→AVE), direction abbreviation, unit/suite removal, punctuation cleanup
- **City normalization:** Standard abbreviation expansion (St→Saint, Ft→Fort, Mt→Mount)
- **State normalization:** Full name to 2-letter abbreviation mapping
- **ZIP normalization:** Extract 5-digit code, zero-pad short codes
- **Owner/management name normalization:** Strip legal suffixes (LLC, Inc, Corp, LP), remove DBA clauses, THE prefix, normalize spacing

### Step 3: Quality Scoring
Every record receives a quality score (0.0–1.0) based on weighted field completeness:

**LIHTC scoring weights:**
| Field | Weight |
|-------|--------|
| HUD ID | 0.10 |
| Project name | 0.15 |
| Address | 0.15 |
| City + State | 0.10 |
| ZIP code | 0.05 |
| Total units | 0.10 |
| LI units | 0.05 |
| Credit type | 0.05 |
| PIS year | 0.10 |
| Owner | 0.10 |
| Coordinates | 0.05 |

### Step 4: Cross-Linking (5 Stages)

1. **Property ID Match** (confidence 1.0): Direct join between multifamily property_id and REAC inspection property_id
2. **Address Match — LIHTC to Multifamily** (confidence 0.85–0.90): Normalized address match keys, then fuzzy matching (token sort ratio ≥ 85%) within same state for unmatched records
3. **Contract Number Match** (confidence 1.0): LIHTC sec8_contract to Section 8 contract_id
4. **Address Match — LIHTC to REAC** (confidence 0.85): Direct address key matching
5. **Owner/Management Profile Aggregation**: Aggregate normalized management company names across LIHTC, multifamily, and Section 8 sources; compute portfolio-level REAC score statistics

### Step 5: Management Company Profiling
For each unique normalized management company name:
- Count total properties managed across all sources
- Sum total housing units
- Compute average and minimum REAC inspection scores
- Count failed inspections (score < 60)
- List all states of operation
- Track which data sources contain properties for this company

## Key Metrics

| Metric | Value |
|--------|-------|
| LIHTC Projects | 54,102 |
| REAC Inspections | 33,772 |
| Multifamily Properties | 36,274 |
| Cross-Links Created | 51,427 |
| Management Companies | 4,556 |
| States/Territories | 56 |
| Total LIHTC Units | 3,718,831 |
| Avg Inspection Score | 89.9 |
| Failing Inspections (<60) | 956 |

## Limitations

1. **REAC scores are most recent only:** The multifamily datasets embed only the last inspection score, not historical scores. Trend analysis is not possible.
2. **LIHTC owner field is sparse:** The HUD User LIHTC CSV does not consistently populate owner/management company fields. Cross-linking to multifamily records partially compensates.
3. **Address matching is imperfect:** Fuzzy matching may produce false positives. All fuzzy links are flagged with confidence scores below 1.0.
4. **Section 8 contracts not yet loaded:** The Section 8 contract data source has not yet been integrated (future enhancement).
5. **Point-in-time snapshot:** This represents a single download of current data, not a longitudinal time series.

## Technical Stack

- Python 3.12, SQLite with WAL mode
- Click CLI for pipeline orchestration
- Streamlit + Plotly for interactive dashboard
- rapidfuzz for fuzzy address matching
- httpx for HTTP downloads
- openpyxl for Excel export styling

## Contact

Built by Nathan Goldberg
Email: nathanmauricegoldberg@gmail.com
LinkedIn: linkedin.com/in/nathanmauricegoldberg
