# Australian Data Centre Atlas / 澳洲数据中心数据看板

A maintained, bilingual (EN / 中文) web dashboard of the Australian data centre sector: every major facility on a map by stage, the
power and fibre infrastructure around them, the federal and state grid-connection regulatory pathways, operator market share and
profiles, and daily news headlines. Built for MAI Capital research.

**Live site:** `https://liquidgz.github.io/au-dc-dashboard/` (after following `DEPLOY_GUIDE.md`)

## How it works

```
 Excel workbook (data/source/ADC_Master_<date>.xlsx)      ← the single source of truth you edit
        │  python scripts/build_data.py
        ▼
 site/data/*.json  ──┬── site/index.html + assets/app.js   (Leaflet map, Chart.js charts, EN/中文 toggle)
                     ├── scripts/fetch_news.py  → news.json     (daily, RSS feeds listed in the workbook)
                     └── scripts/fetch_geo.py   → geo/*.geojson (weekly, Geoscience Australia + TeleGeography)
        │  GitHub Actions (.github/workflows/build-deploy.yml) on push + daily cron
        ▼
 GitHub Pages
```

* **Update data** → `python scripts/new_version.py` → edit the new time-stamped workbook → commit + push. Older versions are kept in `data/archive/`. See `DATA_UPDATE_GUIDE.md`.
* **Deploy** → `DEPLOY_GUIDE_WEB.md` does the whole thing in a browser (no Git install); `DEPLOY_GUIDE.md` is the GitHub Desktop / command-line route.
* **No build tooling**: the site is static HTML/CSS/JS with Leaflet 1.9.4 and Chart.js 4.4.1 vendored in `site/assets/vendor/`. Python 3 + `openpyxl` is the only dependency for the data scripts.

## Contents of the seed (15 Sep 2026)

| Dataset | Rows | Notes |
|---|---|---|
| Facilities | 114 | 49 operational · 20 under construction · 8 approved · 37 planning, all states/territories; owner, operator, stage, IT load (op./planned), year, tenants, grid notes, certifications, EN/中文 description, sources |
| Operators | 29 | colocation, hyperscalers, developers, investors — background (EN/中文), founded, ownership, shareholders, AU MW, investment, 3–4 dated latest moves each |
| Regulation | FED + 8 jurisdictions, 70 steps | step-by-step grid-connection pathway with authority, legal basis, duration, federal/state overlap flags, 32 recent changes |
| Infrastructure points | 122 + 121 NBN POIs | terminal stations, zone substations, power stations, IX/carrier hotels, cable landing stations, Telstra exchanges |
| Market KPIs | 8 | national operational / pipeline / forecast figures with sources |
| News sources | 8 RSS feeds | Google News queries (EN + 中文), DCD, iTnews, AFR |

Research notes and source documentation are in `docs/`.

## Licences & attribution
Code: MIT. Data compiled from public sources for research; see the *Data & sources* tab and `docs/`. Transmission/substation layers © Commonwealth of Australia (Geoscience Australia) CC BY 4.0. Submarine cable geometry © TeleGeography (display only). Basemap © OpenStreetMap contributors, © CARTO.
