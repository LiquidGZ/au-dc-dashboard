#!/usr/bin/env python3
"""
validate_edition.py — check a new workbook edition against the one it supersedes.

The monthly refresh lets an agent edit the live workbook. This is the deterministic gate that
runs afterwards: it does not judge whether a figure is *right*, it checks that the edition is
structurally sound and that every megawatt of movement in the headline is accounted for by a
named facility. A refresh that cannot be reconciled line by line should not reach a pull request.

    python scripts/validate_edition.py                      # live vs newest archived
    python scripts/validate_edition.py --old a.xlsx --new b.xlsx
    python scripts/validate_edition.py --markdown report.md  # also write a PR-ready summary

Exit codes: 0 pass (with or without warnings), 1 regression, 2 could not run.
"""
import argparse
import glob
import os
import re
import sys

try:
    from openpyxl import load_workbook
except ImportError:  # pragma: no cover
    sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "source")
ARC = os.path.join(ROOT, "data", "archive")
TS_RE = re.compile(r"(\d{8})(?:_(\d{4}))?")
IT_BASIS = "IT load"

# A refresh works a review queue; it should not rewrite the database wholesale.
MAX_FACILITY_CHANGES = 40        # rows whose capacity or stage moved
MAX_HEADLINE_SWING = 0.25        # fraction of the previous IT-load total


def key(path):
    m = TS_RE.search(os.path.basename(path))
    return (m.group(1), m.group(2) or "0000") if m else ("0", "0")


def newest(pattern):
    files = [f for f in glob.glob(pattern) if not os.path.basename(f).startswith("~$")]
    return sorted(files, key=key)[-1] if files else None


def read(path):
    """Pull the facility fields the headline depends on, keyed by facility_id."""
    wb = load_workbook(path, read_only=True, data_only=True)
    if "Facilities" not in wb.sheetnames:
        sys.exit(f"[fail] {os.path.basename(path)} has no Facilities sheet")
    ws = wb["Facilities"]
    it = ws.iter_rows(values_only=True)
    hdr = [str(h).strip() if h is not None else "" for h in next(it)]
    ix = {h: i for i, h in enumerate(hdr)}
    for need in ("facility_id", "name", "stage", "it_load_mw_planned", "it_load_mw_operational"):
        if need not in ix:
            sys.exit(f"[fail] {os.path.basename(path)} Facilities is missing column {need!r}")
    out = {}
    for r in it:
        if r is None or all(v in (None, "") for v in r):
            continue
        fid = r[ix["facility_id"]]
        if not fid:
            continue
        basis = (r[ix["capacity_basis"]] if "capacity_basis" in ix else None) or IT_BASIS
        planned = r[ix["it_load_mw_planned"]] or 0
        oper = r[ix["it_load_mw_operational"]] or 0
        out[fid] = {
            "name": r[ix["name"]],
            "stage": r[ix["stage"]],
            "basis": basis,
            "raw": planned or oper,
            "it": (planned or oper) if basis == IT_BASIS else 0,
        }
    counts = {s: wb[s].max_row - 1 for s in wb.sheetnames}
    return out, counts, set(wb.sheetnames)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", help="previous edition; default newest in data/archive")
    ap.add_argument("--new", help="candidate edition; default newest in data/source")
    ap.add_argument("--markdown", help="also write a pull-request summary to this path")
    a = ap.parse_args()

    new_path = a.new or newest(os.path.join(SRC, "*.xlsx"))
    old_path = a.old or newest(os.path.join(ARC, "*.xlsx"))
    if not new_path:
        sys.exit("[fail] no workbook in data/source")
    if not old_path:
        print("[skip] no archived edition to compare against")
        return 0

    old, old_counts, old_sheets = read(old_path)
    new, new_counts, new_sheets = read(new_path)

    problems, warnings, lines = [], [], []

    missing_sheets = old_sheets - new_sheets
    if missing_sheets:
        problems.append(f"sheets dropped: {sorted(missing_sheets)}")

    for s in sorted(old_sheets & new_sheets):
        if new_counts[s] < old_counts[s]:
            problems.append(f"{s}: {old_counts[s]} -> {new_counts[s]} rows (rows were removed)")

    lost = sorted(set(old) - set(new))
    if lost:
        problems.append(f"facility rows lost: {lost}")
    added = sorted(set(new) - set(old))

    old_it = sum(f["it"] for f in old.values())
    new_it = sum(f["it"] for f in new.values())
    delta = new_it - old_it

    # Reconcile the headline movement facility by facility.
    moves = []
    for fid in sorted(set(old) | set(new)):
        o, n = old.get(fid), new.get(fid)
        oi, ni = (o["it"] if o else 0), (n["it"] if n else 0)
        if round(ni - oi, 1) == 0 and (not o or not n or o["basis"] == n["basis"]):
            continue
        label = (n or o)["name"]
        if not o:
            why = f"new row ({n['basis']})"
        elif not n:
            why = "row removed"
        elif o["basis"] != n["basis"]:
            why = f"basis {o['basis']} -> {n['basis']}"
        else:
            why = f"capacity {o['raw']:,.0f} -> {n['raw']:,.0f} MW"
        moves.append((round(ni - oi, 1), fid, label, why))

    reconciled = round(sum(m[0] for m in moves), 1)
    if abs(reconciled - round(delta, 1)) > 0.5:
        problems.append(f"headline delta {delta:+,.1f} MW does not reconcile to the "
                        f"per-facility sum {reconciled:+,.1f} MW")

    changed = [fid for fid in set(old) & set(new)
               if old[fid]["raw"] != new[fid]["raw"] or old[fid]["stage"] != new[fid]["stage"]
               or old[fid]["basis"] != new[fid]["basis"]]
    if len(changed) > MAX_FACILITY_CHANGES:
        problems.append(f"{len(changed)} facility rows changed, above the {MAX_FACILITY_CHANGES} "
                        f"expected of a monthly queue — this looks like a bulk rewrite")
    if old_it and abs(delta) / old_it > MAX_HEADLINE_SWING:
        problems.append(f"headline IT load moved {delta / old_it:+.0%}, beyond the "
                        f"{MAX_HEADLINE_SWING:.0%} sanity bound")

    stage_moves = [(fid, old[fid]["stage"], new[fid]["stage"]) for fid in set(old) & set(new)
                   if old[fid]["stage"] != new[fid]["stage"]]

    lines.append(f"Edition: `{os.path.basename(old_path)}` -> `{os.path.basename(new_path)}`\n")
    lines.append(f"| | previous | new | change |")
    lines.append(f"|---|---:|---:|---:|")
    lines.append(f"| Tracked full-build IT load | {old_it:,.0f} MW | {new_it:,.0f} MW | {delta:+,.0f} MW |")
    lines.append(f"| Facility rows | {len(old)} | {len(new)} | {len(new) - len(old):+d} |")
    for s in ("Operators", "OperatorMoves", "Reg_Changes"):
        if s in old_counts and s in new_counts:
            lines.append(f"| {s} | {old_counts[s]} | {new_counts[s]} | {new_counts[s] - old_counts[s]:+d} |")

    if moves:
        lines.append("\n**Headline movement, reconciled**\n")
        for d, fid, label, why in sorted(moves, key=lambda m: -abs(m[0])):
            lines.append(f"- `{fid}` {d:+,.0f} MW — {label} ({why})")
        lines.append(f"\nSum: {reconciled:+,.0f} MW, matching the headline change.")
    else:
        lines.append("\nNo change to the headline IT-load total.")

    if added:
        lines.append("\n**New rows**: " + ", ".join(f"`{f}`" for f in added))
    if stage_moves:
        lines.append("\n**Stage changes**")
        for fid, o, n in stage_moves:
            lines.append(f"- `{fid}` {o} -> {n}")

    report = "\n".join(lines)
    print(report)

    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print("  [warn]", w)
    if problems:
        print("\nRegressions:")
        for p in problems:
            print("  [fail]", p)

    if a.markdown:
        with open(a.markdown, "w", encoding="utf-8") as fh:
            fh.write(report + "\n")
            if problems:
                fh.write("\n**Validation failed**\n" + "".join(f"\n- {p}" for p in problems) + "\n")
        print(f"\nwrote {a.markdown}")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
