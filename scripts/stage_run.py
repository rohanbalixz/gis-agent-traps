#!/usr/bin/env python3
"""Stage one run: copy its data to a neutral folder and print what to paste.

Usage (system Python is fine, no extra packages):
  python3 scripts/stage_run.py 7        # stage run 7 from runs/run_log.csv
  python3 scripts/stage_run.py --list   # show the run order

Each run gets a fresh folder, ~/gis_work/runNN/, so:
  - the agent never sees this kit's folder names in a file path, and
  - edits the agent makes to a layer (e.g. adding a density field) never carry
    into the next run.
Nothing is ever deleted.
"""
import csv
import shutil
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
WORK = Path.home() / "gis_work"

FILES = {
    "A": ["counties.gpkg"],
    "B": ["pa_counties.gpkg", "fast_food_restaurants.gpkg"],
    "C": ["cities.gpkg"],
}
TASK_NAME = {"A": "county_density", "B": "fastfood_obesity", "C": "city_error"}
DESCRIBE = {
    "counties.gpkg": "Contiguous US county boundaries with 2023 population (GeoPackage, layer 'counties')",
    "pa_counties.gpkg": "Pennsylvania county boundaries with county attributes (GeoPackage, layer 'pa_counties')",
    "fast_food_restaurants.gpkg": "Fast food restaurant locations in Pennsylvania (GeoPackage, layer 'fast_food_restaurants')",
    "cities.gpkg": "City points with model error and city covariates (GeoPackage, layer 'cities')",
}


def load_runs():
    with open(KIT / "runs" / "run_log.csv", newline="") as f:
        return list(csv.DictReader(f))


def main():
    runs = load_runs()
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    if sys.argv[1] == "--list":
        for r in runs:
            print(f"{r['run_order']:>2}  {r['run_id']}")
        return
    n = int(sys.argv[1])
    row = next((r for r in runs if int(r["run_order"]) == n), None)
    if row is None:
        sys.exit(f"No run {n}. Use --list.")
    task, dset, rid = row["task"], row["data_set"], row["run_id"]

    dest = WORK / f"run{n:02d}"
    if dest.exists() and any(dest.iterdir()):
        sys.exit(f"{dest} already has files. If you are redoing run {n}, "
                 f"rename that folder first (e.g. add _old) so nothing is lost.")
    dest.mkdir(parents=True, exist_ok=True)
    for fname in FILES[task]:
        shutil.copy2(KIT / "data" / f"task_{task}" / dset / fname, dest / fname)

    prompt = (KIT / "prompts" / f"task_{task}.txt").read_text().strip()

    tpath = KIT / "runs" / "transcripts" / f"{rid}.md"
    if not tpath.exists():
        tpath.write_text(
            f"# Run {n}: {rid}\n\n"
            "- Date and time (ET):\n- Agent and version:\n- Model:\n"
            "- Attempt that completed (1-3):\n\n"
            f"## Prompt (pasted verbatim)\n\n{prompt}\n\n"
            "## Agent's full response\n\n(paste everything the agent wrote)\n\n"
            "## Generated code\n\n```python\n(paste)\n```\n\n"
            "## Final answer, in the agent's words\n\n\n"
            "## What I observed (before opening the answer key)\n\n"
            "- Generic caveat? (quote)\n- Named the specific problem? (quote)\n"
            "- Fixed it? How?\n- Task A only: which tool or function computed area?\n"
        )

    bar = "-" * 72
    print(f"{bar}\nRun {n} of {len(runs)}: {rid}\n{bar}")
    print(f"Data copied to: {dest}")
    for fname in FILES[task]:
        print(f"  {dest / fname}")
    print(f"Transcript file: {tpath}")
    print(f"\n{bar}\nGIS COPILOT: new QGIS project, add the layer(s) above, start a new chat, paste:\n{bar}")
    print(prompt)
    print(f"\n{bar}\nLLM-GEO fallback: paste into the TASK cell of LLM_Geo_API4.ipynb:\n{bar}")
    print(f"task_name = '{TASK_NAME[task]}_run{n:02d}'")
    print(f'TASK = r"""{prompt}"""')
    print("DATA_LOCATIONS = [")
    for fname in FILES[task]:
        print(f'    "{DESCRIBE[fname]}: {dest / fname}.",')
    print("]")


if __name__ == "__main__":
    main()
