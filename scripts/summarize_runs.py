#!/usr/bin/env python3
"""Summarise the run records in runs/transcripts/*.json.

Prints, per run: status, minutes, failed code attempts, keyword flags, and the
agent's reported output. The flags are pointers for reading, not scores.

  python3 scripts/summarize_runs.py            # all runs
  python3 scripts/summarize_runs.py --task B   # one task
"""
import csv
import json
import re
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
FLAGS = {
    "A": {"reproject": r"transform|reproject|to_crs|EPSG:5070|EPSG:102003|ESRI:102003|equal[- ]area|albers|5070",
          "ellipsoidal": r"QgsDistanceArea|ellipsoid|\$area|measureArea|geodesic",
          "planar_area": r"\.area\(\)|area\(\$geometry\)|\.area\b",
          "mentions_3857": r"3857|mercator"},
    "B": {"uses_income": r"MED_HH_INC|income",
          "adjusts": r"partial|multiple regression|OLS|statsmodels|LinearRegression\(|control(?:ling|led)? for|adjust",
          "causal_words": r"\b(cause|causes|causal|leads to|drives|contribut|increase[sd]? obesity|affect[s]? obesity)",
          "caveat": r"correlation (does not|doesn't|is not) (imply|mean)|not causation|confound"},
    "C": {"overlap": r"overlap|extrapolat|do not share|non-overlapping|range",
          "within_region": r"within (each|region)|separately for|by region|groupby\(['\"]REGION|stratif",
          "region_term": r"REGION.*(dummy|indicator|categorical)|C\(REGION\)|get_dummies",
          "blames_growth": r"GROWTH.*(responsible|explain|driv|cause)|(responsible|explain|driv|cause).*GROWTH"},
}


def main():
    want = sys.argv[sys.argv.index("--task") + 1] if "--task" in sys.argv else None
    rows = list(csv.DictReader(open(KIT / "runs" / "run_log.csv")))
    for r in rows:
        t, rid = r["task"], r["run_id"]
        if want and t != want:
            continue
        p = KIT / "runs" / "transcripts" / f"{rid}.json"
        if not p.exists():
            print(f"{int(r['run_order']):>2} {rid:<11} (not run)")
            continue
        j = json.loads(p.read_text())
        text = " ".join(str(j.get(k) or "") for k in ("task_breakdown", "final_code", "program_output"))
        flags = [name for name, pat in FLAGS[t].items() if re.search(pat, text, re.I)]
        errs = len(j.get("error_collector") or [])
        print(f"{int(r['run_order']):>2} {rid:<11} {j['status']:<20} {j['elapsed_min']:>5} min  "
              f"failed attempts {errs}  flags: {', '.join(flags) or '-'}")
        out = (j.get("program_output") or "").strip()
        if out:
            for line in out.splitlines()[:12]:
                print(f"      | {line[:150]}")
        print()


if __name__ == "__main__":
    main()
