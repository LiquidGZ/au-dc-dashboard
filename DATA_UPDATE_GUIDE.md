# Data update guide — how to maintain the Atlas / 数据维护指南

Everything the site shows is read from **one Excel workbook**. You never edit HTML or JSON.

> **Browser-only route:** if you are not using Git locally, skip to the "Updating the data later" section of
> `DEPLOY_GUIDE_WEB.md` — save the workbook under a new date, upload it to `data/source/` on github.com, and
> the workflow archives the old one and rebuilds by itself. The steps below are the local-Git equivalent.

## The routine (5 minutes) / 常规更新流程

1. **Pull** the latest repo (GitHub Desktop → *Fetch origin* / *Pull*). The daily Action commits news and GIS files, so always pull first.
2. **Start a new version** — in PowerShell in the project folder:
   ```powershell
   python scripts\new_version.py "Added NEXTDC S8; updated CDC MW"
   ```
   This copies `data/source/ADC_Master_20260915.xlsx` to `data/archive/` (frozen) and creates `data/source/ADC_Master_<today>.xlsx`, adding a line to its *Changelog* sheet.
   (Same day twice? A `_HHMM` suffix is added automatically. Build always uses the newest timestamp.)
3. **Edit** the new workbook in Excel. Save. Close Excel (so the `~$` lock file disappears).
4. **Check locally** (optional but recommended):
   ```powershell
   python scripts\build_data.py
   ```
   Warnings such as `WARN facility xyz has no coordinates` tell you what to fix.
5. **Commit + push** (GitHub Desktop: write a summary → *Commit to main* → *Push origin*). Within ~3 minutes the site is live with the new data.

历史版本全部保留在 `data/archive/`，随时可以对比或回滚（把旧文件复制回 `data/source/` 并删除新文件即可）。

## Sheet-by-sheet rules / 各工作表填写规则

| Sheet | One row = | Must-have columns | Notes |
|---|---|---|---|
| **Meta** | one setting | `key`, `value` | Site titles, disclaimer, national narrative, map centre/zoom, news retention. Free text; `*_en` / `*_zh` pairs drive the language toggle. |
| **Facilities** | one data centre / campus | `facility_id` (unique slug), `name`, `operator`, `state`, `lat`, `lng`, `stage` | `stage` must be exactly `Operational`, `Under Construction`, `Approved`, `Planning` or `Withdrawn` (withdrawn projects are hidden on the map until the filter is ticked). `capacity_basis` is `IT load` (default) or `Site/grid power` / `Site generation` — anything other than `IT load` is kept out of the IT-load totals and charts and flagged in the UI. `operator_id` links to Operators (leave blank if no profile). MW = IT load; blank = not disclosed. `sources` = URLs separated by ` \| `. |
| **Operators** | one operator / developer / investor | `operator_id`, `name`, `category` | `au_operational_mw` / `au_pipeline_mw` are the operator-reported totals used for market share; if blank the site falls back to summing disclosed sites. |
| **OperatorMoves** | one dated headline | `operator_id`, `date` (YYYY-MM), `headline_en` | Newest first on the site automatically. Add `headline_zh` + `source`. |
| **Market** | one national KPI | `metric_id`, `label_en`, `value`, `unit` | Set `kpi` to TRUE and give a `kpi_order` to put the metric on the Overview KPI row; three tiles are computed from the tracked data and fill the gaps. Keep `notes` short — it renders under the tile. |
| **Reg_Jurisdictions** | one jurisdiction | `jurisdiction_id` (`FED`, `NSW`, …), `name_en` | Overview text and key bodies. |
| **Reg_Steps** | one step of the connection pathway | `jurisdiction_id`, `step_no`, `title_en`, `detail_en` | `overlap_with` = comma-separated jurisdiction ids that run concurrently (state rows usually `FED`; FED rows list the states where the federal step applies — this drives the overlap matrix). |
| **Reg_Changes** | one recent regulatory change | `jurisdiction_id`, `date`, `summary_en` | |
| **Infrastructure** | one key infrastructure point | `infra_id`, `name`, `category`, `lat`, `lng` | `category` must match one of the layer names used by the map (see existing rows). |
| **NBN_POI** | one NBN point of interconnect | `poi_id`, `name`, `lat`, `lng` | Full list; shown as an optional layer. |
| **NewsSources** | one RSS feed | `source_id`, `url`, `enabled` | Google News RSS query URLs work well: `https://news.google.com/rss/search?q=<query>&hl=en-AU&gl=AU&ceid=AU:en`. `filter_keywords` (comma list) keeps only matching items — use it for broad feeds like DCD. Set `enabled` to `FALSE` to pause a feed. |
| **Changelog** | one version | `version_file`, `date`, `notes` | Appended automatically by `new_version.py`; add detail as you like. |

### Do / don't
* ✅ Add rows anywhere; add new columns **to the right** — they flow into the JSON untouched (useful for your own notes).
* ✅ Keep `facility_id` / `operator_id` stable — they are the join keys and appear in URLs.
* ✅ Put a source URL and `last_verified` date on every changed row.
* ❌ Don't rename sheet tabs or header cells.
* ❌ Don't type "N/A" or "?" in numeric cells — leave them blank.
* ❌ Don't estimate undisclosed MW — the methodology promises blanks, not guesses.

## Adding a whole new layer or field to the site
The site is plain HTML/JS in `site/`. `scripts/build_data.py` passes any extra workbook column straight through, so a new column is available in the browser as `facility.<column_name>` immediately; showing it only needs a line in `site/assets/app.js` (`showDetail()` for the side panel, `COLS` for the table). UI labels are in `site/assets/i18n.js` (EN + 中文).

## Where the GIS layers come from (and how to refresh by hand)
`python scripts\fetch_geo.py` downloads Geoscience Australia *Electricity Infrastructure* (transmission lines ≥132 kV, substations ≥132 kV; CC BY 4.0) and TeleGeography submarine-cable geometry into `site/data/geo/`. The Action does this weekly; run it manually if your network allows (`docs/infra_sources.md` documents every endpoint, licence and fallback). AEMO does not publish a GIS transmission layer — its ISP maps, connection-point lists and the "Rosetta" market portal are documented there as reference sources.
