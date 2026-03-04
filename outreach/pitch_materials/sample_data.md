# HUD Affordable Housing Compliance Tracker — Sample Data

## Top 10 Management Companies by Portfolio Size

| Rank | Management Company | Properties | Avg REAC Score | Failed Inspections | States |
|------|-------------------|-----------|----------------|-------------------|--------|
| 1 | ARC OF NORTH CAROLINA | 344 | 95.2 | 0 | NC |
| 2 | NATIONAL CHURCH RESIDENCES | 135 | 92.5 | 0 | 17 states |
| 3 | SILVER TREE RESIDENTIAL | 126 | 94.7 | 0 | 17 states |
| 4 | CAPITAL REALTY | 123 | 94.6 | 0 | 17 states |
| 5 | PROPERTY MANAGEMENT | 110 | 90.9 | 0 | 18 states |
| 6 | MILLENNIA HOUSING MANAGEMENT | 109 | 82.4 | 2 | 17 states |
| 7 | MERCY HOUSING MANAGEMENT | 108 | 91.6 | 0 | 16 states |
| 8 | FPI MANAGEMENT | 101 | 92.1 | 0 | 10 states |
| 9 | ACCESSIBLE SPACE | 100 | 94.0 | 0 | 17 states |
| 10 | RA MANAGEMENT | 95 | 92.6 | 0 | 15 states |

## Sample Failing Properties (Score < 60)

| Property Name | City | State | Score | Units | Management Company |
|--------------|------|-------|-------|-------|-------------------|
| [Redacted] | Detroit | MI | 12 | 200 | [Available in full dataset] |
| [Redacted] | Chicago | IL | 18 | 150 | [Available in full dataset] |
| [Redacted] | Memphis | TN | 22 | 120 | [Available in full dataset] |
| [Redacted] | Houston | TX | 25 | 250 | [Available in full dataset] |
| [Redacted] | New York | NY | 28 | 180 | [Available in full dataset] |

*Full property names and management company linkages available in the complete dataset.*

## LIHTC Projects by Credit Type

| Credit Type | Projects | Total Units | Avg Quality Score |
|------------|----------|-------------|-------------------|
| 4% | 14,000+ | 1.2M+ | 0.72 |
| 9% | 38,000+ | 2.4M+ | 0.68 |
| Both | 2,000+ | 150K+ | 0.75 |

## Cross-Link Coverage

| Link Type | Count | Confidence |
|-----------|-------|------------|
| Multifamily → REAC (property ID) | 33,772 | 1.00 |
| LIHTC → Multifamily (address) | 13,314 | 0.85–0.90 |
| LIHTC → REAC (address) | 4,341 | 0.85 |

## Data Quality Distribution

- Records with quality score ≥ 0.8: 75%+
- Records with quality score ≥ 0.5: 95%+
- Records with geocoding (lat/lon): 85%+

---

*Full dataset includes 124,148 total records with 51,427 cross-links.*
*Contact: Nathan Goldberg — nathanmauricegoldberg@gmail.com*
