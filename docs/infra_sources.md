# GIS sources for Australian data-centre ancillary infrastructure (power + fibre)

Researched 15 Sep 2026. Everything marked **[validated]** was fetched live on that date (via the Anthropic
WebFetch proxy, which can reach the hosts) and returned the described payload. Everything marked
**[not testable from sandbox]** could not be curl-tested because the Claude sandbox egress policy
answers `CONNECT 403` for those hosts; the URL is still given and its status explained.

## 0. Sandbox limitation you must know about

From the Bash sandbox, **every** Australian government / ArcGIS host was blocked by the organisation
egress policy (`services.ga.gov.au`, `digital.atlas.gov.au`, `data.gov.au`, `pid.geoscience.gov.au`,
`ecat.ga.gov.au`, `hub.arcgis.com`, `services.arcgis.com`, `www.arcgis.com`, `aemo.com.au`,
`nbn.rinseout.org`, `nbnco.com.au`). `raw.githubusercontent.com` is reachable only for repositories
attached to the session. Therefore `fetch_geo.py` was **validated against a local mock ArcGIS server**
(`mock_arcgis.py`), and the live endpoints were validated with WebFetch instead (query URL, fields,
counts, sample features). **You must run `fetch_geo.py` on your own machine** (see section 9).

---

## 1a. Geoscience Australia – Electricity Transmission Lines ("Power Lines")  [validated]

| Item | Value |
|---|---|
| Current service (v3.1.0, 2026) | `https://services.ga.gov.au/gis/rest/services/Electricity_Infrastructure/MapServer` |
| Layer | **2 – Power Lines** (polyline). Layer 0 = Substations, Layer 1 = Major Power Stations |
| Legacy service | `https://services.ga.gov.au/gis/rest/services/National_Electricity_Infrastructure/MapServer` (layers 0 Substations / 1 Major Power Stations / 2 Electricity Transmission Lines). Layer metadata still resolves (fields `CAPACITYKV`, `OPERATIONALSTATUS`, `NAME`, `CLASS`, `STATE`) but `/query` returned **HTTP 404** on 15 Sep 2026 – treat as deprecated and use `Electricity_Infrastructure`. |
| FeatureServer? | No – `.../Electricity_Infrastructure/FeatureServer` → 500 "extension not found". MapServer supports `Query` (capabilities `Map,Query,Data`). |
| Digital Atlas of Australia page | `https://digital.atlas.gov.au/datasets/digitalatlas::power-lines/about` (item id `70f23e91102a4d6899a776d093fa08ef`, layer 2, recordCount **3,147**, modified 19 Jun 2026) |
| Catalogue | GA eCat / PID `https://pid.geoscience.gov.au/dataset/ga/151179` (redirects into eCat SPA); metadata PDF `https://d28rz98at9flks.cloudfront.net/151179/151179_00_3.pdf` |
| Licence | **CC BY 4.0** – "© Commonwealth of Australia (Geoscience Australia) 2026" |
| Formats | REST query: `f=json` (Esri JSON), `f=geojson`, `f=pbf`; maxRecordCount **2000**, `supportsPagination: true`, `supportsAdvancedQueries: true` (distinct values, statistics, orderBy) |
| Fields | `OBJECTID, FEATURE_TYPE, FEATURE_SUBTYPE (Overhead / Underground / Overhead/underground), FEATURE_NAME, FEATURE_DESCRIPTION, STATUS, CAPACITY_KV (smallint), STATE, FEATURE_SOURCE, FEATURE_SOURCE_DATE, ATTRIBUTE_SOURCE, ATTRIBUTE_SOURCE_DATE, SPATIAL_CONFIDENCE, SUPPLIED_FEATURE_EDITS, CREATED_DATE, LAST_EDITED_ON, GLOBALID, SHAPE, st_length(shape)` |
| STATUS domain (distinct, validated) | `Operational`, `Under Construction`, `Non-Operational` |
| Size | whole layer ≈ 9 MB GeoJSON (Hub download). ≥132 kV operational subset ≈ 5–8 MB unsimplified; 5-decimal rounding cuts ~30 %. |

**Query that returns GeoJSON (tested pattern, replace `f=pjson` with `f=geojson` in production):**

```
https://services.ga.gov.au/gis/rest/services/Electricity_Infrastructure/MapServer/2/query
  ?where=CAPACITY_KV%3E%3D132+AND+STATUS%3D%27Operational%27
  &outFields=FEATURE_NAME,FEATURE_SUBTYPE,CAPACITY_KV,STATUS,STATE
  &returnGeometry=true&outSR=4326
  &resultOffset=0&resultRecordCount=1000&orderByFields=OBJECTID
  &f=geojson
```

Validated results (15 Sep 2026):
* `where=CAPACITY_KV>=330 … resultRecordCount=3` → features "Sydney West to Bannaby" (330, Operational, NSW), "Stockdill to Williamsdale" (330), "Wodonga Terminal to Jindera" (330), `exceededTransferLimit: true`.
* `where=CAPACITY_KV>=132&returnCountOnly=true` → **1,693**
* `where=CAPACITY_KV>=132 AND STATUS='Operational'&returnCountOnly=true` → **1,677**

Filtering notes: use `CAPACITY_KV >= 132` for the transmission map (GA includes lines down to 66 kV; some
sub-transmission 110 kV in QLD/WA – include with `>=110` if you want Powerlink/Western Power 110/132 kV
sub-transmission). `CAPACITY_KV` can be `NULL` for some lines – `CAPACITY_KV >= 132` excludes them; add `OR CAPACITY_KV IS NULL` if you want to see them.

**Bulk alternative (no paging, whole layer, `where` must be `1=1`) [validated]:**
`https://hub.arcgis.com/api/v3/datasets/70f23e91102a4d6899a776d093fa08ef_2/downloads/data?format=geojson&spatialRefId=4326&where=1%3D1`
(also reachable via `https://digital.atlas.gov.au/api/download/v1/items/70f23e91102a4d6899a776d093fa08ef/geojson?layers=2`, which 302-redirects to the Hub URL). Returns a `FeatureCollection` named `Power_Lines`. A custom `where` (e.g. `VOLTAGE_KV >= 330`) returned **404** – Hub only serves its cached full extract, so filter locally. Formats also available: `format=shp|csv|kml|fgdb`.

## 1b. Geoscience Australia – Electricity Transmission Substations ("Substations")  [validated]

| Item | Value |
|---|---|
| REST layer | `https://services.ga.gov.au/gis/rest/services/Electricity_Infrastructure/MapServer/0` (point) |
| Digital Atlas | `https://digital.atlas.gov.au/datasets/digitalatlas::substations/about` (item `d5eae2d7c9e54581a5f19d7e95b9883b`, layer 0, recordCount **1,866**, modified 19 Jun 2026) |
| Licence | CC BY 4.0 (GA) |
| Fields | `OBJECTID, FEATURE_TYPE, FEATURE_SUBTYPE, FEATURE_NAME, FEATURE_DESCRIPTION, STATUS, VOLTAGE_KV (smallint), LOCALITY, STATE, FEATURE_SOURCE, FEATURE_SOURCE_DATE, ATTRIBUTE_SOURCE, ATTRIBUTE_SOURCE_DATE, SPATIAL_CONFIDENCE, LATITUDE, LONGITUDE, CREATED_DATE, LAST_EDITED_ON, GLOBALID, SHAPE` |
| Size | ≥132 kV subset ≈ 250–350 KB GeoJSON |

Query (validated with `f=pjson`, 3 features returned incl. Mt Emerald 275 kV QLD, Tumoulin 275 kV, Guybal Munjan 275 kV "Under Construction"; `exceededTransferLimit: true`):

```
https://services.ga.gov.au/gis/rest/services/Electricity_Infrastructure/MapServer/0/query
  ?where=VOLTAGE_KV%3E%3D132
  &outFields=FEATURE_NAME,VOLTAGE_KV,STATUS,STATE,LOCALITY
  &returnGeometry=true&outSR=4326&resultOffset=0&resultRecordCount=1000&f=geojson
```
`where=VOLTAGE_KV>=132&returnCountOnly=true` → **982** features. Filter: `VOLTAGE_KV >= 132` (terminal/bulk-supply), `VOLTAGE_KV >= 220` (terminal stations only), `STATUS='Operational'` optional (GA includes Under Construction / Non-Operational; keep them but style differently – e.g. Swanbank B 275 kV is Non-Operational).

Handy `find` endpoint for name look-ups (validated): `…/Electricity_Infrastructure/MapServer/find?searchText=Rocklea&searchFields=FEATURE_NAME&contains=true&layers=0&returnGeometry=true&sr=4326&f=json`.

Bulk: `https://hub.arcgis.com/api/v3/datasets/d5eae2d7c9e54581a5f19d7e95b9883b_0/downloads/data?format=geojson&spatialRefId=4326&where=1%3D1` [validated – first features Clements Gap Wind Farm 132 kV, etc.]

## 1c. Geoscience Australia – Major Power Stations  [validated]

* `https://services.ga.gov.au/gis/rest/services/Electricity_Infrastructure/MapServer/1` (point), CC BY 4.0.
* Fields (lower-case on this layer): `feature_name, owner, primary_fuel_type, primary_fuel_type_descriptor, technology_type, generation_capacity_mw (double), number_of_units, status, locality, state, latitude, longitude, …`
* Query validated: `…/1/query?where=generation_capacity_mw+%3E+700&outFields=*&returnGeometry=false&f=pjson` → 22 rows (Eraring 2,880 MW, Bayswater 2,640, Liddell 2,200, Loy Yang A 2,180, Gladstone 1,680, Hazelwood 1,600 "Decommissioned", …).
* **Caveat:** owner/status attributes are stale in places (Liddell still "Operational", Yallourn owner "Truenergy") – use for location only and overlay AEMO Generation Information for status/MW.
* Filter suggestion: `generation_capacity_mw >= 100 AND status <> 'Decommissioned'`.

## 1d. AEMO – "Rosetta", ISP maps and transmission data  [partially validated]

* **"Rosetta" could not be located on aemo.com.au** (tried `/rosetta`, `rosetta.aemo.com.au`, ISP and Forecasting-data sections; WebSearch quota was exhausted). If the user means AEMO's interactive network/ISP map, the public artefacts that exist are below. **Action for user:** confirm the exact URL/product name (it may be a login-only participant tool on the AEMO Market Portal `https://portal.prod.nemnet.net.au`, which needs registration).
* AEMO does **not** publish a downloadable GIS layer of the NEM transmission network – it points to Geoscience Australia (above). What it does publish:
  * **2026 ISP page** `https://www.aemo.com.au/energy-systems/major-publications/integrated-system-plan-isp/2026-integrated-system-plan-isp` [validated] with GIS files: REZ boundaries KMZ `https://www.aemo.com.au/-/media/files/major-publications/isp/2026/supporting-materials/indicative-rez-boundaries-2026-gis-data.kmz` and sub-regional boundaries KMZ `…/indicative-subregional-boundaries-2026-gis-data.kmz`; 2024 KML: `…/isp/2024/supporting-materials/indicative-rez-boundaries-2024-gis-data.kml`. Convert KMZ→GeoJSON with `ogr2ogr` or `fastkml`.
  * **Transmission augmentation information** `https://www.aemo.com.au/energy-systems/electricity/national-electricity-market-nem/nem-forecasting-and-planning/forecasting-and-planning-data/transmission-augmentation-information` (tables of committed/anticipated projects – HumeLink, VNI West, Sydney Ring, etc.; not GIS – geocode the terminal stations from the GA layer).
  * **NEM generation / connection-interest maps (PDF)** `https://www.aemo.com.au/-/media/files/electricity/nem/network_connections/generation-maps/nsw-map.pdf` (qld/sa/tas/vic/nem_regional_boundaries) – updated 12 Dec 2025.
  * **NEM regional boundaries map (PDF)** `https://www.aemo.com.au/-/media/files/electricity/nem/planning_and_forecasting/maps/nem-regional-boundaries-map-web.pdf`.
  * **Enhanced Locational Information (ELI) 2025** `https://www.aemo.com.au/…/forecasting-and-planning-data/enhanced-locational-information` – congestion/hosting-capacity metrics per connection point (PDF + Excel chart data) – useful to score substations for DC connection feasibility.
  * **Transmission Connection Point Forecasting** – per-connection-point demand forecasts (Excel), joinable to GA substation names.
  * **Generation Information** (Excel, monthly) – authoritative MW/status for the power-station layer.
* How to use: draw the network from GA; join AEMO ELI/connection-point tables by substation name for capacity colouring; overlay ISP REZ/sub-region KMZ; annotate committed projects manually.
* TNSP alternatives with real GIS: Transgrid Transmission Annual Planning Report maps, Powerlink "Network Map", Western Power Network Capacity Mapping Tool (`https://www.westernpower.com.au/industry/calculators-tools/network-capacity-mapping-tool/`) – interactive, no bulk export.

## 1e. NBN Points of Interconnect (121 POIs) with coordinates  [validated]

* **Coordinates source:** community CSV "Hypothetical NBN POI Addresses" by dleonard0 – `https://gist.github.com/dleonard0/27a707e149d061ed0a1d18009e485e77` (file `POIs.csv`, columns `Name, Ref, Geolocation, Address`, 121 rows; 5 "Interim Agg" rows lack coords). This is the dataset nbn.rinseout.org credits for POIs. Raw: `https://gist.githubusercontent.com/dleonard0/27a707e149d061ed0a1d18009e485e77/raw/POIs.csv` (robots-blocked for bots, fine for you). Licence: none stated (treat as community/unlicensed; addresses are public Telstra exchange addresses).
  * Full list extracted and saved to **`nbn_pois.csv`** in this folder (I corrected one obvious error: Grafton 2GRN carried Newcastle coordinates; replaced with approximate Grafton exchange coords – verify).
* **nbn.rinseout.org** – unofficial site; pages: `/national.php`, `/state.php?id=NSW` (table "POI ID | Name | Telstra Exchange | Locations" – 42 NSW POIs), `/csa.php?id=CSA…` (Connectivity Serving Area → POI id/name), `/fsa.php?id=…`. It has **no public JSON API and no coordinates**; POI code ↔ Telstra ESA code (e.g. 2CHA → CHAT) is the useful join key. Sitemaps: `https://nbn.rinseout.org/sitemap-main.xml.gz`, `-fsams`, `-das-1/2`. Attribution page lists its sources: G-NAF, ACMA SIP dataset (`https://data.gov.au/data/dataset/statutoryinfrastructureprovidernbncolimited`), the POI gist above, GA Telephone Exchanges service, Whirlpool exchange guide.
* Official: NBN Co publishes the POI list as a PDF/XLSX in its Wholesale Broadband Agreement "NBN Co POI List" (nbnco.com.au → Sell → WBA documents) – addresses only, no lat/lng. Geocode against GA Telephone_Exchanges (below) using the Telstra ESA code.

## 1f. Telstra exchanges with coordinates  [validated – feasible]

* **Geoscience Australia "National Telephone Exchanges"** ArcGIS service: `https://services.ga.gov.au/gis/rest/services/Telephone_Exchanges/MapServer/0` – **2,017 points** (count validated), CC BY 4.0 (© GA 2015 – vintage 2011–2015 but exchange buildings rarely move). Fields: `name, operationalstatus, exchangeserviceareaid (ESA code, e.g. DKIN), address, suburb, state, spatialconfidence, revised, featuretype, class, description`. Query: `…/Telephone_Exchanges/MapServer/0/query?where=1%3D1&outFields=*&returnGeometry=true&outSR=4326&resultOffset=0&resultRecordCount=1000&f=geojson` (2 pages + 17). Filter major exchanges by ESA code list (PITT, KENT, DALL, EXHI, LONS, EDIS, WELL, WAYM, CIVC, HOBT…) or by joining to the POI list's "Telstra Exchange" column.
* Whirlpool "Australian exchange guide" wiki `https://whirlpool.net.au/wiki/australian_exchange_guide` – per-exchange pages with addresses (robots-blocked to bots; manual use only).
* Feasibility: **high** – GA layer gives coordinates + ESA codes for all ~2,000 exchanges; only ~10 "major" ones need hand tagging (done in `infra_points.json`).

## 1g. Submarine cables & landing stations  [validated]

* **TeleGeography live API (public, no key), same JSON that backs the GitHub repo:**
  * Landing points GeoJSON: `https://www.submarinecablemap.com/api/v3/landing-point/landing-point-geo.json` – FeatureCollection `landing_points`, properties `id, name, is_tbd`, Point geometry (~500 features worldwide, ~150 KB). Australian ids include `alexandria-nsw-australia [151.19621,-33.91367]`, `brookvale-nsw-australia [151.27399,-33.76116]`, `maroochydore-qld-australia [153.08944,-26.65184]`, `port-hedland-wa-australia [118.57724,-20.31346]`, `darwin-nt-australia [130.84315,-12.46749]`, `perth-wa-australia [115.86177,-31.94955]`, `sandy-point-vic-australia`, `inverloch-vic-australia`, `mcgaurans-beach-vic-australia`, `four-mile-bluff-tas-australia`, `stanley-tas-australia`, `boat-harbour-tas-australia`, `wurrumiyanga-nt-australia`, plus `sydney-nsw-australia`, `oxford-falls-nsw-australia`, `paddington-nsw-australia`, `clovelly-nsw-australia`, `maroubra-nsw-australia`, `torquay-vic-australia`, `melbourne-vic-australia`, `adelaide-sa-australia`, `brisbane-qld-australia`, `mandurah-wa-australia`, `cape-jervis-sa-australia`, `kingscote-sa-australia`, `alyangula-nt-australia`, `numbulwar-nt-australia`.
  * Cable routes GeoJSON: `https://www.submarinecablemap.com/api/v3/cable/cable-geo.json` (properties `id, name, color, feature_id`; MultiLineString; ~5 MB).
  * Country summary (validated, full JSON obtained): `https://www.submarinecablemap.com/api/v3/country/australia.json` – 35 cables with `rfs_year`, `is_planned`, `landing_points[]`. Operational: AJC, ASC, Bass Strait-1/2, Basslink, Coral Sea (CS²), DJSC, Gondwana-1, Groote Eylandt, Hawaiki, INDIGO-Central/West, JGA-S, Kangaroo Island 2, NWCS, OAC, PPC-1, SCCN, Southern Cross NEXT, SMAP (2026), TGA, Telstra Endeavour. Planned: APX East 2028, ACC-1 2029, Bernacchi-1 2027, Bosun 2029, Hawaiki Nui 1 2027, Honomoana 2026, Project Waterworth, SX-TX 2028, Tabua 2026, TalayLink 2028, Tasman Ring 2029, Umoja 2028.
  * Per-object: `…/api/v3/cable/<id>.json`, `…/api/v3/landing-point/<id>.json` (cable list, no coords – coords live only in `landing-point-geo.json`).
* **GitHub repo** `https://github.com/telegeography/www.submarinecablemap.com` – historically the same files under `web/public/api/v3/…` (branch `master`). `raw.githubusercontent.com/telegeography/www.submarinecablemap.com/master/web/public/api/v3/landing-point/landing-point-geo.json` returned **404 from this sandbox** (the repo is not attached to the session, and GitHub raw paths may have changed) – use the live API above, or `git clone` and look under `web/public/api/v3/`.
* Licence: TeleGeography data is free for non-commercial use with attribution ("© TeleGeography, submarinecablemap.com"); commercial redistribution requires their licence – for an internal dashboard, attribute and do not redistribute raw files.
* Caveat: TeleGeography places "Sydney"/"Perth"/"Melbourne" at generic city points; real CLS buildings (Oxford Falls, Paddington, Brookvale, Alexandria, Cromer, Shenton Park/Floreat) are hand-placed in `infra_points.json` with "approximate" flags.

## 1h. Internet exchanges / carrier hotels  [validated]

* **IX Australia PoP list** `https://ix.asn.au/services/peering/` [validated] – 7 IXs / 28 DCs: NSW-IX (Equinix SY1/2 639 Gardeners Rd Mascot; DigiCo SYD1 400 Harris St Ultimo; Equinix SY3 47 Bourke Rd Alexandria; Equinix SY4/5 200 Bourke Rd Alexandria; NEXTDC S1 4 Eden Park Dr & S2 6/8 Giffnock Ave Macquarie Park; Fujitsu 23-25 Waterloo Rd North Ryde; Macquarie IC2 17-23 Talavera Rd), VIC-IX (NEXTDC M1 826 Lorimer St; Equinix ME1 578 Lorimer St; Vocus VDC-MEL03 & MelbDC 530 Collins St), QLD-IX (NEXTDC B1 20 Wharf St; B2 454 St Pauls Tce), WA-IX (Vocus 1 William St; NEXTDC P2 11 Newcastle St; Equinix PE2 37 Lemnos St Shenton Park; NEXTDC P1 4 Millrose Dr Malaga), SA-IX (NEXTDC A1 125 Frome St; DigiCo ADL1 Edinburgh Parks; DigiCo ADL2 60 Belair Rd Hawthorn; Colocity DC3 172 Morphett St), ACT-IX (NEXTDC C1 19 Battye St Bruce; TransACT 470 Northbourne Ave), TAS-IX (7HOB POI; TasmaNet DC3 Dowsing Point). No coordinates – geocode addresses.
* **Megaport public locations API** `https://api.megaport.com/v2/locations` [validated, no auth] – JSON with `name, address{street,suburb,city,state,postcode,country}, latitude, longitude, metro, dc{name}` for every Megaport-enabled DC worldwide (~900; filter `country == "Australia"` → ~90 sites incl. Equinix SY1 (-33.921867, 151.18802), SY3 (-33.91217, 151.19382), DigiCo SYD1 (-33.87555, 151.19783), NEXTDC S1 (-33.785065, 151.13121), M1 (-37.822006, 144.9324), B1 (-27.46549, 153.02963) …). **Best single source of carrier-hotel coordinates** – licence: Megaport API terms (public, attribute).
* Equinix site pages give addresses (e.g. `https://www.equinix.com/data-centers/asia-pacific-colocation/australia-colocation/sydney-data-centers/sy4` → "200 Bourke Road, Alexandria"; ME1 → "578 Lorimer Street, Port Melbourne"); NEXTDC `https://www.nextdc.com/data-centres` lists codes + suburb + MW (S1 16, S2 30, S3 80, S4 365, S5 80+, S6 13.5, S7 550+, M1 16, M2 120+, M3 225, M4 150, B1 2.25, B2 12, P1 10+, P2 20+, C1 4.4, A1 5, D1 1, D2 6+, SC1 1, SC2 6, GC1 6, PH1 1, NE1 1, GE1 4).
* PeeringDB (`https://www.peeringdb.com/api/fac?country=AU`, public JSON, lat/lng for most facilities) is the other good bulk source – not tested here.
* "1 Wilson St": the only "1 Wilson St" in the datasets is the Bassendean WA NBN POI (6BSD); no Sydney carrier hotel by that address was found – please confirm what you meant.

---

## 9. Running `fetch_geo.py`

```
python3 fetch_geo.py ./geo_out
```
* Standard library only. Pages `…/MapServer/2/query` and `…/0/query` with `resultOffset`/`resultRecordCount=1000` (`GA_PAGE_SIZE` env to change), stops when `exceededTransferLimit` is false. Requests `f=geojson`, falls back to `f=json` + local Esri→GeoJSON conversion, then to the Hub bulk GeoJSON (where=1=1) with local filtering. Coordinates rounded to 5 dp; property keys lower-cased; `metadata` block records source/licence/filter/count.
* Expected output (counts validated 15 Sep 2026): `transmission_lines.geojson` **1,677** features (≈5–7 MB), `substations.geojson` **982** features (≈300 KB).
* Mock test result (local ArcGIS emulator, both geojson and Esri-JSON paths): 1,368 lines / 1,036 substations across 2 pages each – pagination, fallback and rounding verified.
* If your network also blocks GA, download the two Hub GeoJSON files in a browser and point the script at them (or just filter them with any GeoJSON tool).
