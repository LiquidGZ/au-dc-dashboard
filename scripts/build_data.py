#!/usr/bin/env python3
"""
build_data.py — convert the NEWEST master workbook in data/source/ into the JSON files the site reads.

    python scripts/build_data.py            # auto-picks newest data/source/ADC_Master_*.xlsx
    python scripts/build_data.py path.xlsx  # or an explicit workbook

Outputs (site/data/):
    meta.json, facilities.json, operators.json, market.json, regulations.json,
    infrastructure.json, nbn_poi.json, news_sources.json, stats.json, build_info.json

Rules the workbook must follow (see README sheet): sheet names and header cells are looked up by
name; extra columns are passed through untouched; multi-value cells use ' | ' (sources) or ', '.
"""
import glob
import json
import os
import re
import sys
import datetime as dt
from collections import defaultdict

try:
    from openpyxl import load_workbook
except ImportError:  # pragma: no cover
    sys.exit("openpyxl is required:  pip install -r scripts/requirements.txt")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "data", "source")
OUT_DIR = os.path.join(ROOT, "site", "data")

STAGES = ["Operational", "Under Construction", "Approved", "Planning", "Withdrawn"]
# Facilities whose headline MW is site/grid power or generation rather than IT load are excluded
# from IT-load totals and reported separately (Facilities.capacity_basis).
IT_BASIS = "IT load"
TS_RE = re.compile(r"(\d{8})(?:_(\d{4}))?")


def newest_workbook():
    files = glob.glob(os.path.join(SRC_DIR, "ADC_Master_*.xlsx"))
    files = [f for f in files if not os.path.basename(f).startswith("~$")]
    if not files:
        sys.exit(f"No ADC_Master_*.xlsx found in {SRC_DIR}")

    def key(f):
        m = TS_RE.search(os.path.basename(f))
        return (m.group(1), m.group(2) or "0000") if m else ("0", "0")

    return sorted(files, key=key)[-1]


def rows(ws):
    """Yield dicts keyed by header row; skip fully-empty rows."""
    it = ws.iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else "" for h in next(it)]
    for r in it:
        if r is None or all(v in (None, "") for v in r):
            continue
        d = {}
        for h, v in zip(header, r):
            if not h:
                continue
            if isinstance(v, str):
                v = v.strip()
                if v == "":
                    v = None
            if isinstance(v, (dt.datetime, dt.date)):
                v = v.isoformat()[:10]
            d[h] = v
        yield d


def split(v, sep="|"):
    if v is None:
        return []
    if isinstance(v, (int, float)):
        return [str(v)]
    return [s.strip() for s in str(v).split(sep) if s.strip()]


def num(v):
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def to_bool(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "1", "yes", "y")


def dump(name, obj):
    os.makedirs(OUT_DIR, exist_ok=True)
    p = os.path.join(OUT_DIR, name)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
    print(f"  wrote {name:22s} {os.path.getsize(p)/1024:7.1f} KB")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else newest_workbook()
    print(f"Building from {os.path.relpath(path, ROOT)}")
    wb = load_workbook(path, read_only=True, data_only=True)
    need = ["Meta", "Facilities", "Operators", "OperatorMoves", "Market", "Reg_Jurisdictions",
            "Reg_Steps", "Reg_Changes", "Infrastructure", "NBN_POI", "NewsSources"]
    missing = [s for s in need if s not in wb.sheetnames]
    if missing:
        sys.exit(f"Workbook is missing sheets: {missing}")

    # ---- Meta
    meta = {}
    for r in rows(wb["Meta"]):
        if r.get("key"):
            meta[r["key"]] = r.get("value")
    for k in ("map_center_lat", "map_center_lng", "map_zoom", "news_days_to_keep", "news_max_items"):
        if k in meta:
            meta[k] = num(meta[k])
    dump("meta.json", meta)

    # ---- Facilities
    facilities = []
    for r in rows(wb["Facilities"]):
        if not r.get("facility_id"):
            continue
        for k in ("lat", "lng", "it_load_mw_operational", "it_load_mw_planned", "site_area_ha", "capex_aud_m"):
            r[k] = num(r.get(k))
        for k in ("year_announced", "year_commissioned"):
            v = num(r.get(k))
            r[k] = int(v) if v else None
        r["sources"] = split(r.get("sources"))
        if r.get("stage") not in STAGES:
            print(f"  WARN facility {r['facility_id']} has unknown stage '{r.get('stage')}'")
        if r["lat"] is None or r["lng"] is None:
            print(f"  WARN facility {r['facility_id']} has no coordinates — will not appear on the map")
        facilities.append(r)
    dump("facilities.json", facilities)

    # ---- Operators + moves
    moves = defaultdict(list)
    for r in rows(wb["OperatorMoves"]):
        if r.get("operator_id"):
            moves[r["operator_id"]].append(r)
    for k in moves:
        moves[k].sort(key=lambda m: str(m.get("date") or ""), reverse=True)
    operators = []
    for r in rows(wb["Operators"]):
        if not r.get("operator_id"):
            continue
        for k in ("au_operational_mw", "au_pipeline_mw", "announced_investment_aud_bn"):
            r[k] = num(r.get(k))
        for k in ("founded_year", "au_facility_count"):
            v = num(r.get(k))
            r[k] = int(v) if v else None
        r["sources"] = split(r.get("sources"))
        r["latest_moves"] = moves.get(r["operator_id"], [])
        operators.append(r)
    dump("operators.json", operators)

    # ---- Market KPIs
    market = []
    for r in rows(wb["Market"]):
        if r.get("metric_id"):
            r["value"] = num(r.get("value"))
            r["kpi"] = to_bool(r.get("kpi"))
            r["kpi_order"] = num(r.get("kpi_order"))
            market.append(r)
    market.sort(key=lambda m: (m["kpi_order"] is None, m["kpi_order"] or 0))
    dump("market.json", market)

    # ---- Regulations
    steps = defaultdict(list)
    for r in rows(wb["Reg_Steps"]):
        if not r.get("jurisdiction_id"):
            continue
        r["step_no"] = int(num(r.get("step_no")) or 0)
        r["overlap_with"] = split(r.get("overlap_with"), ",")
        r["sources"] = split(r.get("sources"))
        steps[r["jurisdiction_id"]].append(r)
    changes = defaultdict(list)
    for r in rows(wb["Reg_Changes"]):
        if r.get("jurisdiction_id"):
            changes[r["jurisdiction_id"]].append(r)
    jurisdictions = []
    for r in rows(wb["Reg_Jurisdictions"]):
        if not r.get("jurisdiction_id"):
            continue
        jid = r["jurisdiction_id"]
        r["sources"] = split(r.get("sources"))
        r["steps"] = sorted(steps.get(jid, []), key=lambda s: s["step_no"])
        r["recent_changes"] = sorted(changes.get(jid, []), key=lambda c: str(c.get("date") or ""), reverse=True)
        jurisdictions.append(r)
    order = ["FED", "NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"]
    jurisdictions.sort(key=lambda j: order.index(j["jurisdiction_id"]) if j["jurisdiction_id"] in order else 99)
    dump("regulations.json", {
        "jurisdictions": jurisdictions,
        "overlap_notes_en": meta.get("overlap_notes_en"),
        "overlap_notes_zh": meta.get("overlap_notes_zh"),
    })

    # ---- Infrastructure
    infra = []
    for r in rows(wb["Infrastructure"]):
        if not r.get("infra_id"):
            continue
        r["lat"], r["lng"], r["voltage_kv"] = num(r.get("lat")), num(r.get("lng")), num(r.get("voltage_kv"))
        if r["lat"] is not None and r["lng"] is not None:
            infra.append(r)
    dump("infrastructure.json", infra)
    nbn = []
    for r in rows(wb["NBN_POI"]):
        r["lat"], r["lng"] = num(r.get("lat")), num(r.get("lng"))
        if r.get("poi_id") and r["lat"] is not None:
            nbn.append(r)
    dump("nbn_poi.json", nbn)

    # ---- News sources (read by fetch_news.py)
    news_sources = []
    for r in rows(wb["NewsSources"]):
        if r.get("url"):
            r["enabled"] = to_bool(r.get("enabled", True))
            r["filter_keywords"] = split(r.get("filter_keywords"), ",")
            news_sources.append(r)
    dump("news_sources.json", news_sources)

    # ---- Derived statistics for the dashboard
    op_by_id = {o["operator_id"]: o for o in operators}
    def fullbuild(f):
        """Full-build IT load: planned where disclosed, else operational. 0 for non-IT-load bases."""
        if (f.get("capacity_basis") or IT_BASIS) != IT_BASIS:
            return 0
        return f.get("it_load_mw_planned") or f.get("it_load_mw_operational") or 0

    def other_basis(f):
        """Announced MW for facilities that publish only site/grid power or generation capacity."""
        if (f.get("capacity_basis") or IT_BASIS) == IT_BASIS:
            return 0
        return f.get("it_load_mw_planned") or f.get("it_load_mw_operational") or 0

    agg = defaultdict(lambda: {"operational_mw_sites": 0.0, "planned_mw_sites": 0.0, "count": 0,
                               "by_stage": {s: 0 for s in STAGES},
                               "mw_by_stage": {s: 0.0 for s in STAGES}, "disclosed_sites": 0})
    for f in facilities:
        key = f.get("operator_id") or f.get("operator") or "Unknown"
        a = agg[key]
        a["count"] += 1
        if f.get("stage") in STAGES:
            a["by_stage"][f["stage"]] += 1
            a["mw_by_stage"][f["stage"]] += fullbuild(f)
        if f.get("it_load_mw_operational"):
            a["operational_mw_sites"] += f["it_load_mw_operational"]
            a["disclosed_sites"] += 1
        if f.get("it_load_mw_planned"):
            a["planned_mw_sites"] += f["it_load_mw_planned"]
    op_stats = []
    for key, a in agg.items():
        o = op_by_id.get(key)
        name = o["name"] if o else key
        reported = o["au_operational_mw"] if o else None
        # Best estimate = operator-reported figure where available, else sum of disclosed per-site figures
        best = reported if reported is not None else (a["operational_mw_sites"] or None)
        basis = "operator-reported" if reported is not None else ("sum of disclosed sites" if best else "not disclosed")
        pipeline = (o["au_pipeline_mw"] if o and o["au_pipeline_mw"] is not None
                    else max(a["planned_mw_sites"] - (best or 0), 0) or None)
        pbasis = "operator-reported" if (o and o["au_pipeline_mw"] is not None) else ("planned minus operational (sites)" if pipeline else "not disclosed")
        op_stats.append({
            "operator_id": o["operator_id"] if o else None, "name": name, "has_profile": bool(o),
            "category": o["category"] if o else None,
            "operational_mw": best, "operational_basis": basis,
            "pipeline_mw": pipeline, "pipeline_basis": pbasis,
            "announced_investment_aud_bn": o["announced_investment_aud_bn"] if o else None,
            "facility_count": a["count"], "by_stage": a["by_stage"],
            "mw_by_stage": a["mw_by_stage"], "fullbuild_mw": round(sum(a["mw_by_stage"].values()), 1),
        })
    # investors / operators with a profile but no facility rows still appear
    for o in operators:
        if o["operator_id"] not in agg:
            op_stats.append({
                "operator_id": o["operator_id"], "name": o["name"], "has_profile": True, "category": o["category"],
                "operational_mw": o["au_operational_mw"], "operational_basis": "operator-reported" if o["au_operational_mw"] is not None else "not disclosed",
                "pipeline_mw": o["au_pipeline_mw"], "pipeline_basis": "operator-reported" if o["au_pipeline_mw"] is not None else "not disclosed",
                "announced_investment_aud_bn": o["announced_investment_aud_bn"],
                "facility_count": 0, "by_stage": {s: 0 for s in STAGES},
                "mw_by_stage": {s: 0.0 for s in STAGES}, "fullbuild_mw": 0,
            })
    total_op = sum(s["operational_mw"] or 0 for s in op_stats)
    for s in op_stats:
        s["share_of_tracked_operational"] = round(100 * (s["operational_mw"] or 0) / total_op, 1) if total_op else None
    op_stats.sort(key=lambda s: (-(s["operational_mw"] or 0), -(s["pipeline_mw"] or 0)))

    by_state = defaultdict(lambda: {"count": 0, "by_stage": {s: 0 for s in STAGES},
                                    "mw_by_stage": {s: 0.0 for s in STAGES},
                                    "operational_mw": 0.0, "planned_mw": 0.0, "fullbuild_mw": 0.0,
                                    "other_basis_mw": 0.0})
    by_stage = {s: {"count": 0, "planned_mw": 0.0} for s in STAGES}
    for f in facilities:
        st = by_state[f.get("state") or "?"]
        st["count"] += 1
        if f.get("stage") in STAGES:
            st["by_stage"][f["stage"]] += 1
            st["mw_by_stage"][f["stage"]] += fullbuild(f)
            by_stage[f["stage"]]["count"] += 1
            by_stage[f["stage"]]["planned_mw"] += fullbuild(f)
        if f.get("stage") != "Withdrawn":
            st["operational_mw"] += f.get("it_load_mw_operational") or 0
        st["planned_mw"] += f.get("it_load_mw_planned") or 0
        st["fullbuild_mw"] += fullbuild(f)
        st["other_basis_mw"] += other_basis(f)

    dump("stats.json", {
        "operators": op_stats,
        "tracked_operational_mw_total": round(total_op, 1),
        "by_state": by_state, "by_stage": by_stage,
        "facility_count": len(facilities),
        "other_basis_mw_total": round(sum(other_basis(f) for f in facilities), 1),
        "disclosed_operational_mw_sites": round(sum(f.get("it_load_mw_operational") or 0 for f in facilities), 1),
        "planned_mw_sites": round(sum(f.get("it_load_mw_planned") or 0 for f in facilities), 1),
    })

    # copy the workbook next to the JSON so the site can offer it for download
    import shutil
    wb_dir = os.path.join(OUT_DIR, "workbook")
    os.makedirs(wb_dir, exist_ok=True)
    for old in glob.glob(os.path.join(wb_dir, "*.xlsx")):
        os.remove(old)
    shutil.copy2(path, os.path.join(wb_dir, os.path.basename(path)))

    dump("build_info.json", {
        "workbook": os.path.basename(path),
        "built_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "counts": {"facilities": len(facilities), "operators": len(operators), "jurisdictions": len(jurisdictions),
                   "infrastructure_points": len(infra), "nbn_poi": len(nbn), "news_sources": len(news_sources)},
    })
    print("Done.")


if __name__ == "__main__":
    main()
