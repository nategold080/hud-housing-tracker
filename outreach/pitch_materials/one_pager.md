# HUD Affordable Housing Compliance Tracker

## The Problem
HUD's affordable housing data is fragmented across multiple systems. LIHTC allocations, REAC inspections, and multifamily property records exist in separate databases with no standard way to connect them. This makes it impossible to answer basic accountability questions: Which management companies consistently fail inspections? Are LIHTC tax credit dollars going to well-maintained properties?

## The Solution
The first cross-linked database connecting three HUD data systems into a unified, queryable dataset with management company accountability profiles.

## By the Numbers

| Metric | Value |
|--------|-------|
| LIHTC Projects | 54,102 |
| REAC Inspections | 33,772 |
| Multifamily Properties | 36,274 |
| Entity Cross-Links | 51,427 |
| Management Companies | 4,556 |
| States/Territories | 56 |
| Total Housing Units | 3.7M+ |
| Failing Properties | 956 |

## Key Insights

**Management Company Accountability:**
- 4,556 management companies profiled with portfolio-level REAC scores
- Largest companies manage 100–300+ properties across 15+ states
- Several major management companies average REAC scores below 80 (national avg: 89.9)
- 956 properties with failing scores (<60) linked to responsible management entities

**Geographic Patterns:**
- LIHTC allocation patterns by state from 1987–2023
- State-level inspection score variations
- Congressional district coverage analysis

**Cross-Link Value:**
- 13,314 LIHTC-to-multifamily connections via address matching
- 33,772 multifamily-to-REAC connections via property ID
- 4,341 direct LIHTC-to-REAC connections

## Deliverables
- SQLite database with full query capabilities
- Interactive Streamlit dashboard (8 sections)
- CSV, JSON, and Excel exports
- Full methodology documentation
- Management company profiles with inspection score tracking

## Use Cases
- **Compliance monitoring:** Track management company performance across portfolios
- **Investment due diligence:** LIHTC syndicators can assess management company track records
- **Policy research:** Connect tax credit allocation decisions to property quality outcomes
- **Investigative journalism:** Identify patterns of poor property maintenance by large operators
- **Advocacy:** Data-driven arguments for affordable housing quality standards

## Contact
**Nathan Goldberg**
nathanmauricegoldberg@gmail.com
linkedin.com/in/nathanmauricegoldberg
