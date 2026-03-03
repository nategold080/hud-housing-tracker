# Problems Tracker — HUD Affordable Housing Compliance Tracker

## P1: CLIENT_GROUP_NAME is not owner — DONE
- `CLIENT_GROUP_NAME` in multifamily ArcGIS data is tenant category (Elderly, Family), not owner
- Fixed: Map `MGMT_AGENT_ORG_NAME` to `owner_name` instead
- Result: Owner profiles jumped from 19 fake categories to 4,556 real management companies

## P2: LIHTC download URL — DONE
- Original URL `lihtc.huduser.gov/resources/LIHTCPUB.csv` returns 404
- Fixed: Use `www.huduser.gov/lihtc/lihtcpub.zip` (ZIP containing CSV)
- Added ZIP extraction with CSV fallback in download_lihtc()

## P3: LIHTC CSV has no owner field populated — OPEN
- 0/54,102 LIHTC records have owner or mgmt_company fields populated
- The HUD User CSV simply doesn't include this data
- Workaround: Management company data comes from multifamily ArcGIS instead
- Future: LIHTC ArcGIS FeatureServer has OWNER_CONTACT_NAME/OWNER_ORG_NAME for ~50K projects

## P4: Section 8 contracts not yet integrated — OPEN
- Section 8 contract data would add another cross-linking dimension
- Source: HUD Section 8 Contracts ArcGIS FeatureServer
- Impact: Would enable contract expiration tracking and additional owner data

## P5: REAC scores are most recent only — OPEN (structural limitation)
- Multifamily ArcGIS only exposes last inspection score, not historical
- No public API for historical REAC data
- Impact: Cannot do trend analysis on inspection scores over time
