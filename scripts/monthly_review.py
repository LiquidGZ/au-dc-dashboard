#!/usr/bin/env python3
"""
monthly_review.py — turn the month's collected headlines into a review queue.

Run by .github/workflows/monthly-review.yml on the 1st of each month. It reads the news archive and the
built data, and writes a markdown brief that the workflow posts as a GitHub issue. It changes NO data —
it only tells you what probably needs changing, with links, so the workbook edit takes minutes.

    python scripts/monthly_review.py                 # last full month
    python scripts/monthly_review.py --since 2026-09-01
    python scripts/monthly_review.py --out review.md --json review.json

What it looks for
  1. Headlines carrying a change signal (approved, refused, withdrawn, commissioned, MW revision,
     acquisition, lease, IPO, policy) and which facility or operator they mention.
  2. Rows going stale: facilities not re-verified in 90+ days, weighted by size and stage.
  3. Regulatory items whose stated date has now passed (determinations due, consultations closing).
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "data")

# Signal → what kind of workbook edit it usually implies
SIGNALS = [
    ("Stage change", ["approve", "approved", "approval", "refuse", "refused", "reject", "knock back",
                      "withdraw", "withdrawn", "determination", "consent", "green light", "gives the nod",
                      "construction start", "starts construction", "breaks ground", "sod turn",
                      "commission", "commissioned", "goes live", "went live", "opens", "opened",
                      "energise", "energised", "energize", "first power", "lodge", "lodged", "exhibition"]),
    ("Capacity / capex", ["mw", "megawatt", "gw", "gigawatt", "expansion", "expand", "stage two", "stage 2",
                          "capacity", "upsize", "scaled back", "billion", "capex"]),
    ("Ownership / capital", ["acquire", "acquisition", "acquires", "buys", "sale", "sells", "stake", "ipo",
                             "float", "listing", "raise", "raising", "fund", "reit", "merger", "joint venture",
                             "partnership", "consortium", "valuation", "recapitalis"]),
    ("Tenant / contract", ["lease", "leases", "anchor", "tenant", "signs", "signed", "contract", "offtake",
                           "agreement", "mou", "pre-commit", "precommit"]),
    ("Regulation / grid", ["aemc", "aemo", "aer", "rule change", "determination", "guideline", "guidelines",
                           "bill", "legislation", "regulation", "standard", "standards", "consultation",
                           "planning rules", "policy", "moratorium", "connection queue", "transgrid",
                           "vicgrid", "powerlink", "western power", "electranet", "tasnetworks"]),
]
STALE_DAYS = 90


def load(name, default=None):
    try:
        with open(os.path.join(DATA, name), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return default if default is not None else []


GENERIC = {"data", "centre", "center", "campus", "the", "and", "for", "of", "stage", "park", "project",
           "hyperscale", "digital", "facility", "site", "pty", "ltd", "limited", "group", "new", "one", "two",
           "north", "south", "east", "west", "western", "eastern", "northern", "southern", "central", "greater",
           "road", "street", "drive", "avenue", "lane", "way", "precinct", "hub", "energy", "infrastructure",
           "former", "plant", "mill", "works", "old", "proposed", "australia", "australian", "power",
           "technology", "technologies", "cloud", "network", "networks", "stage1", "phase"}


def name_tokens(name):
    return [t.lower() for t in re.findall(r"[A-Za-z][A-Za-z0-9']{2,}", name or "")
            if t.lower() not in GENERIC]


def build_matcher(facilities):
    """A facility only matches a headline on tokens that are distinctive to it.

    Tokens are scored by how many facility names contain them: 'melbourne' or 'nextdc' appear in dozens, so
    they identify nothing; 'glendenning' or 'kurri' appear once. A match needs either two distinctive tokens,
    or one distinctive token plus the operator's name — which keeps 'Fujitsu Western Sydney' from catching
    every Sydney headline.
    """
    df = defaultdict(int)
    per_fac = {}
    for f in facilities:
        toks = set(name_tokens(f.get("name", "")) + name_tokens((f.get("city_suburb") or "").split(",")[0]))
        per_fac[f["facility_id"]] = toks
        for t in toks:
            df[t] += 1
    index = []
    for f in facilities:
        ident = {t for t in per_fac[f["facility_id"]] if df[t] <= 2 and len(t) >= 4}
        index.append((f, ident, (f.get("operator") or "").lower()))
    return index


def match_facility(blob_low, index):
    best, best_score = None, 0
    for f, ident, op in index:
        if not ident:
            continue
        hits = sum(1 for t in ident if re.search(r"\b" + re.escape(t) + r"\b", blob_low))
        if not hits:
            continue
        op_hit = bool(op) and op.split(" (")[0] in blob_low
        if hits >= 2 or (hits >= 1 and op_hit):
            score = hits * 2 + (1 if op_hit else 0)
            if score > best_score:
                best, best_score = f, score
    return best


def month_bounds(today):
    first_this = today.replace(day=1)
    last_month_end = first_this - dt.timedelta(days=1)
    return last_month_end.replace(day=1), first_this


def classify(text):
    hits = []
    low = text.lower()
    for label, words in SIGNALS:
        for w in words:
            if re.search(r"\b" + re.escape(w) + r"\b", low):
                hits.append(label)
                break
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="ISO date; default is the start of last month")
    ap.add_argument("--until", help="ISO date; default is the start of this month")
    ap.add_argument("--out", default=os.path.join(ROOT, "review", "latest.md"))
    ap.add_argument("--json", dest="json_out", default=os.path.join(ROOT, "review", "latest.json"))
    args = ap.parse_args()

    today = dt.date.today()
    d0, d1 = month_bounds(today)
    if args.since:
        d0 = dt.date.fromisoformat(args.since)
    if args.until:
        d1 = dt.date.fromisoformat(args.until)

    news = load("news.json", {"items": []})
    facilities = load("facilities.json")
    operators = load("operators.json")
    regs = load("regulations.json", {"jurisdictions": []})

    window = [i for i in news.get("items", []) if d0.isoformat() <= (i.get("published") or "")[:10] < d1.isoformat()]
    window.sort(key=lambda i: i["published"], reverse=True)

    # ---- 1. headlines that look like data changes
    fac_index = build_matcher(facilities)
    by_facility, by_operator, regulatory, other = defaultdict(list), defaultdict(list), [], []
    flagged = 0
    for it in window:
        blob = f"{it.get('title','')} {it.get('summary','')}"
        sig = classify(blob)
        if not sig:
            continue
        flagged += 1
        low = blob.lower()
        hit = match_facility(low, fac_index)
        matched = False
        if hit:
            by_facility[hit["facility_id"]].append((it, sig))
            matched = True
        if not matched and it.get("operators"):
            by_operator[it["operators"][0]].append((it, sig))
            matched = True
        if not matched:
            (regulatory if "Regulation / grid" in sig else other).append((it, sig))

    # ---- 2. rows going stale
    def days_since(v):
        try:
            return (today - dt.date.fromisoformat(str(v)[:10])).days
        except (TypeError, ValueError):
            return 9999

    stale = [f for f in facilities if days_since(f.get("last_verified")) > STALE_DAYS]
    stale.sort(key=lambda f: -(f.get("it_load_mw_planned") or f.get("it_load_mw_operational") or 0))
    live_stages = {"Under Construction", "Approved", "Planning"}
    stale_live = [f for f in stale if f.get("stage") in live_stages][:15]

    # ---- 3. regulatory dates that have passed
    due = []
    date_pat = re.compile(r"\b(\d{1,2}\s+)?(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(20\d{2})\b")
    months = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}
    for j in regs.get("jurisdictions", []):
        for s in j.get("steps", []):
            for m in date_pat.finditer(s.get("detail_en", "") or ""):
                day = int((m.group(1) or "1").strip())
                try:
                    when = dt.date(int(m.group(3)), months[m.group(2)], min(day, 28))
                except ValueError:
                    continue
                if when < today and (today - when).days < 400:
                    due.append((j["jurisdiction_id"], s["step_no"], s.get("title_en", ""), m.group(0)))
    seen = set()
    due = [d for d in due if not (d[:2] + (d[3],) in seen or seen.add(d[:2] + (d[3],)))][:20]

    # ---- write the brief
    facs = {f["facility_id"]: f for f in facilities}
    label = d0.strftime("%B %Y")
    L = [f"# Monthly data review — {label}",
         "",
         f"Window: **{d0} → {d1 - dt.timedelta(days=1)}** · {len(window)} headlines collected, "
         f"**{flagged}** carry a change signal · archive now holds {news.get('total_items', len(news.get('items', [])))} items.",
         "",
         "Nothing below has been changed. Work through it, edit the workbook, save it under a new date, "
         "and upload it to `data/source/` — the site rebuilds itself.",
         ""]

    if by_facility:
        L += ["## Facilities named in the news", ""]
        for fid, rows in sorted(by_facility.items(), key=lambda kv: -len(kv[1])):
            f = facs.get(fid, {})
            mw = f.get("it_load_mw_planned") or f.get("it_load_mw_operational")
            L.append(f"### {f.get('name', fid)} — currently *{f.get('stage','?')}*"
                     f"{f', {mw:g} MW' if mw else ''} · `{fid}`")
            for it, sig in rows[:6]:
                L.append(f"- [ ] {it['published'][:10]} · **{' / '.join(sig)}** · "
                         f"[{it['title']}]({it['link']}){' — ' + it['publisher'] if it.get('publisher') else ''}")
            L.append("")

    if by_operator:
        L += ["## Operators named in the news", ""]
        for op, rows in sorted(by_operator.items(), key=lambda kv: -len(kv[1])):
            L.append(f"### {op}")
            for it, sig in rows[:6]:
                L.append(f"- [ ] {it['published'][:10]} · **{' / '.join(sig)}** · "
                         f"[{it['title']}]({it['link']}){' — ' + it['publisher'] if it.get('publisher') else ''}")
            L.append("")

    if regulatory:
        L += ["## Regulation and grid", ""]
        for it, sig in regulatory[:20]:
            L.append(f"- [ ] {it['published'][:10]} · [{it['title']}]({it['link']})"
                     f"{' — ' + it['publisher'] if it.get('publisher') else ''}")
        L.append("")

    if other:
        L += ["<details><summary>Other flagged headlines (no facility or operator matched)</summary>", ""]
        for it, sig in other[:30]:
            L.append(f"- {it['published'][:10]} · [{it['title']}]({it['link']})")
        L += ["", "</details>", ""]

    if due:
        L += ["## Regulatory dates that have now passed", "",
              "These are dates written into the regulation steps. Check the outcome and update the step text.", ""]
        for jid, step, title, when in due:
            L.append(f"- [ ] **{jid}** step {step} — {title} *(mentions {when})*")
        L.append("")

    if stale_live:
        L += [f"## Pipeline rows not re-verified in {STALE_DAYS}+ days", "",
              "Largest first, limited to projects still moving.", ""]
        for f in stale_live:
            mw = f.get("it_load_mw_planned") or f.get("it_load_mw_operational")
            L.append(f"- [ ] {f['name']} ({f.get('state')}, {f.get('stage')}"
                     f"{f', {mw:g} MW' if mw else ''}) — last verified {f.get('last_verified') or 'never'} · `{f['facility_id']}`")
        L += ["", f"*{len(stale)} of {len(facilities)} rows are over {STALE_DAYS} days old in total.*", ""]

    if not (by_facility or by_operator or regulatory or due or stale_live):
        L += ["Nothing flagged this month. The archive is still collecting — "
              "check the News tab if that seems wrong.", ""]

    L += ["---",
          "*Generated by `scripts/monthly_review.py`. It reads the news archive and the built data and "
          "changes nothing. Close this issue when the workbook has been updated.*"]

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    with open(args.json_out, "w", encoding="utf-8") as fh:
        json.dump({
            "window": [d0.isoformat(), d1.isoformat()], "label": label,
            "headlines_in_window": len(window), "flagged": flagged,
            "facilities": {k: [i["link"] for i, _ in v] for k, v in by_facility.items()},
            "operators": {k: [i["link"] for i, _ in v] for k, v in by_operator.items()},
            "regulatory": [i["link"] for i, _ in regulatory],
            "dates_passed": [{"jurisdiction": a, "step": b, "title": c, "mentions": d} for a, b, c, d in due],
            "stale_facilities": [f["facility_id"] for f in stale],
        }, fh, ensure_ascii=False, indent=1)

    print(f"{label}: {len(window)} headlines, {flagged} flagged, {len(by_facility)} facilities, "
          f"{len(by_operator)} operators, {len(due)} dates passed, {len(stale_live)} stale rows")
    print(f"wrote {os.path.relpath(args.out, ROOT)} and {os.path.relpath(args.json_out, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
