# Research notes — refresh of 7 Oct 2026

Window swept: 15 Sep – 7 Oct 2026, plus a backfill pass for facilities that predate the original seed.

## What changed structurally

- New stage **Withdrawn** — projects formally pulled after lodgement (Goodman Project Mars 90 MW Lane Cove West, GreenSquareDC Hazelmere 120 MW). Off by default in the map filter; included in tables and operator charts.
- New column **capacity_basis** on Facilities: `IT load` (default) or `Site/grid power` / `Site generation`. Ten projects publish only gross site or generation capacity (Zerra Western Downs, Beetaloo Weddell, Energy North Ares, Akaysha Muswellbrook, Gingerah Meridien, Aurora, Mayfield, Plumpton, Keppel Morwell, Moss Vale). They are now excluded from IT-load totals and charts, and flagged in the popup and detail panel.
  - Effect: tracked full-build IT load reads **16.8 GW** rather than 25.3 GW, with 12.6 GW reported separately on a site/grid-power basis. The 16.8 GW sits close to JLL's independent 16.2 GW national pipeline, which is a useful cross-check.
- New columns **kpi / kpi_order** on Market: tick a metric to put it on the Overview KPI row and set its position, without touching code.

## Facilities

- 20 added (5 new in-window projects, 15 backfilled gaps found by auditing Baxtel/Cloudscene/RenewMap/state registers against the index).
- 10 updated, including: Microsoft Honeman Close approved (SSD-58601963, 96 MW, A$1.26bn, 1 Oct); 2 Glendenning Road approved (SSD-73761707, 193.6 MW, A$2.17bn, 14 Sep — AWS widely reported as end user but not named in the application); Goodman Project Mars withdrawn; Centuria Clayton 38 MW refused by Monash (W.Media only — single source); Zerra Western Downs anchored by Anthropic; AirTrunk Kurri Kurri EIS lodged with A$3.7bn capex and a A$37m community package; GreenSquareDC SYD1 anchored by Sharon AI.
- Index corrections: `nextdc-m4` moved Planning → Approved (VIC permit PA2504019, 16 Jan 2026); `aws-mickleham` annotated with permit PA2604506.
- Open: `stockland-mpark-stage2` carries 100 MW but the March consent (SSD-63235720) is 76.4 MW — reconcile at the next pass. `keppel-morwell-latrobe` 720 MW is gross site power (flagged via capacity_basis).

## Operators

- **Firmus / CDC Project Southgate ended 6 Oct 2026** after only 42 MW of the intended 1.6 GW was deployed at CDC's Melbourne site. The dashboard's largest single pipeline number was retired: Firmus `au_pipeline_mw` and `announced_investment_aud_bn` are now blank, so the figure falls back to the sum of its tracked Australian sites. The three Firmus-owned Tasmanian builds share the Southgate name but were not part of the ended arrangement.
- Firmus priced an ASX IPO at A$11.00 (1 Oct), ~A$7.1bn raise; ownership fields will need revisiting after listing.
- 4 operators added: Zerra DC, HyperDC, Sharon AI, IREN. 13 profiles updated, 21 dated moves added.
- Left unchanged on purpose: AirTrunk pipeline stays 2,400 MW (no source restates the Australian total after Kurri Kurri); CDC stays 550/810 MW (the 16 Sep 'deployed and earning' 350 MW is a different definition, not a revision); CDC announced investment stays A$4.0bn although Wagga alone is up to A$15bn — needs a methodology decision on whether that field is cumulative announced capex.
- Still open at 7 Oct: AirTrunk's US$1.5bn Singapore REIT had not launched; the STACK APAC sale process had no in-window milestone.

## Regulation

- Commonwealth: PM&C consultation paper *Getting it right* (17 Sep) proposes tiered scope — under 30 MW excluded, 30–100 MW baseline, >100 MW (or 150 MW portfolio) substantial; submissions closed 9 Oct, legislation still flagged for early 2027. AEMC initiated both Bowen cost-recovery rule changes (24 Sep): draft determination 1 Apr 2027, final 22 Jul 2027 — NER augmentation cost allocation cannot change before mid-2027.
- Victoria: Sustainable Data Centre Action Plan (22 Sep) — stand-alone 'data centre' land-use term, prohibition in residential and Green Wedge zones with a 150 m dwelling buffer, new-renewables-plus-storage offset, full causer-pays connection, design WUE ≤1.0/≤1.6, VicGrid as statutory referral authority on every application.
- Queensland: from 2 Oct, data centre applications move from councils to State assessment through SARA on the renewables model (SIA plus community benefit agreement before lodgement). Regulation and thresholds unpublished.
- NSW: the EII Amendment Bill 2026 passed the Legislative Assembly 15 Sep and sits with the Legislative Council — the 5 MW large-load access scheme power is not yet law and no scheme is declared.
- AEMC ERC0394 still has no final determination (target 29 Oct 2026, already extended once); the 30 MW threshold remains draft. ERC0455 has not been initiated.
- NT formally opposed mandatory full renewable offsetting (25 Sep), reopening what National Cabinet appeared to settle. SA's AI Royal Commission terms of reference expressly exclude data centres (1 Oct) and the Data Centre and AI Infrastructure Bill is still not introduced.
- No change found for ACT, WA, TAS (consultation closed 12 Oct, final Expectations due end-2026), EPBC/NEPA, FIRB, SOCI or the Hosting Certification Framework.

## Verification gaps

- NSW Bill passage rests on a secondary digest — legislation.nsw.gov.au returned 403.
- QLD and VIC changes are announced policy, not yet gazetted instruments.
- Centuria Clayton refusal and a few facility details are single-source (noted in the row's description).
- News items were gathered by manual sweep because this environment cannot reach news hosts; the daily GitHub Action merges live RSS on top.
