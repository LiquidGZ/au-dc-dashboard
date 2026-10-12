# Research notes — seed of 15 Sep 2026

Items the researchers flagged as uncertain; verify before relying on them.

## Facilities
- NSW IDA "endorsed" (Mar 2026) projects are recorded as **Planning** (fast-track endorsement ≠ planning consent): Microsoft Honeman Close, Stockland/EdgeConneX Davis Road, Stockland/Fife Kemps Creek, ISPT Julius Ave, Glendenning Rd, AIMS Bella Vista, STACK SYD01, NEXTDC S5/S7, Goodman Atlas (Atlas construction start Sep 2026 per Goodman — check stage).
- Conflicting MW: AirTrunk SYD3 (320 vs 400), NEXTDC S4 (232 vs 350 — official 350 used), STACK SYD01 capex ($650m filing vs $3.7bn EDC), Project Pluto (126→68 MW after re-lodgement). See `power_source_notes`.
- Operational MW is blank where operators do not disclose per site (NEXTDC S3, CDC Eastern Creek, Digital Realty, Microsoft, AWS, Fujitsu). Operator-level totals in the Operators sheet fill the gap for market share.
- Approximate coordinates: Macquarie IC4/IC5 Canberra (address unpublished), Fujitsu Greystanes, GreenSquareDC SYD1, CDC Marsden Park precinct, AirTrunk MEL2 Mickleham (press-inferred), several early-stage campuses placed at suburb centroids.
- Single-source entries: Mayfield Energy Precinct 1 GW (RenewMap), Plumpton "Victorian AI Hub" 2.4 GW (RenewMap + parliamentary petition), Stockland Brooklyn 100 MW (derived).
- Excluded: GreenSquareDC WAi1 Perth (withdrawn May 2026), "Growing Australia" Geelong concept, Lane Cove DC Alliance Mars Rd (no MW). No verifiable Yass/Marchmont, Wollongong, Yatala, Crestmead, Kwinana, Jandakot or Port Adelaide proposals were found at seed time — add them when public.
- Vantage MEL1 / STACK MEL02 targeted 2026 in-service; left as Under Construction pending commissioning news.

## Operators
- CDC operating capacity: 302 / 550 / 671 MW across sources — Infratil June-2026 valuation figure (550 MW, includes NZ) used.
- AirTrunk: operational MW not split from the "1.2 GW+ platform"; pipeline 2,400 MW = platform + Kemps Creek 1.2 GW (facility power, not IT load).
- Hyperscaler MW (AWS, Microsoft, Google, Oracle) mostly leased inside colocation halls — do not add to operator totals.
- Dexus, GPT, Mirvac, Charter Hall, Hickory: no verifiable 2025–26 Australian DC commitments found at seed time; omitted rather than guessed.

## Regulation
- Several NSW fee/threshold figures (A$30k/MW bond, A$200k/A$100k per MW upgrade fees, ≥5 MW access schemes) are proposals in the EII Amendment Bill 2026 pending regulations.
- Victorian DFP dollar thresholds, the SA late-2025 Code amendment reference, some NER sub-clause numbering for loads (e.g. S5.3.11), WA planning thresholds and NT/ACT statutory periods are hedged in the step text.
- Pending national items to track: AEMC ERC0394 final determination (29 Oct 2026), AEMO ERC0455 registration/visibility rule change, Commonwealth data-centre energy legislation (early 2027), SA Data Centre & AI Infrastructure Act (announced Jun 2026), Tasmania Draft Expectations consultation (closes 12 Oct 2026), ACT Data Centre Framework draft (early 2027).

## Infrastructure
- ~25 curated points are geocoded from addresses or beach/building positions (carrier hotels, cable landing stations, some Telstra exchanges) — spot-check.
- NBN POI coordinates come from the community gist that nbn.rinseout.org credits (one Grafton error corrected); rinseout itself only maps POIs to Telstra ESAs. Five "interim aggregation" POIs have no public location and are excluded.
- "AEMO Rosetta": no public GIS layer found on aemo.com.au; AEMO's ISP REZ/sub-region KMZ, connection-point list and generation information pages are documented in `infra_sources.md` as substitutes. Geoscience Australia's Electricity Infrastructure service is the authoritative open transmission dataset.
