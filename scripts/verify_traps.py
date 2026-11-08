#!/usr/bin/env python3
"""Check the six shipped datasets against the answer key. No QGIS and no model needed.

Recomputes every number in answer_keys/verification.json from data/ (except the
500-seed robustness shares, which need the Census inputs; see build_and_verify.py)
and prints the headline numbers that make each trap a trap.

  python scripts/verify_traps.py        # exit code 0 if everything matches
"""
import json
import math
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "scripts"))
from build_and_verify import verify_a, verify_b, verify_c  # noqa: E402

key = json.loads((KIT / "answer_keys" / "verification.json").read_text())
sets, data = key["sets"], KIT / "data"
fresh = {"A": {}, "B": {}, "C": {}}
for v in ("trap", "clean"):
    fresh["A"][v] = verify_a(data / "task_A" / sets["A"][v] / "counties.gpkg")
    fresh["B"][v] = verify_b(data / "task_B" / sets["B"][v])
    fresh["C"][v] = verify_c(data / "task_C" / sets["C"][v] / "cities.gpkg")


def same(a, b):
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, str) or isinstance(b, str):
        return str(a) == str(b)
    return math.isclose(float(a), float(b), rel_tol=1e-6, abs_tol=1e-9)


bad = [(t, v, k) for t in "ABC" for v in ("trap", "clean")
       for k, val in key[t][v].items() if not same(fresh[t][v].get(k), val)]

f = fresh
print("Task A  counties above 100/km2, planar area in the file's CRS:"
      f"  trap {f['A']['trap']['count_above_planar']}  clean {f['A']['clean']['count_above_planar']}"
      f"  (true: {f['A']['trap']['count_above_true']})")
print("Task A  median density, planar:"
      f"  trap {f['A']['trap']['median_density_planar']:.2f}  clean {f['A']['clean']['median_density_planar']:.2f}"
      f"  (true: {f['A']['trap']['median_density_true']:.2f})")
print("Task B  partial r (score vs obesity | income):"
      f"  trap {f['B']['trap']['partial_r_income']:+.3f} (p={f['B']['trap']['partial_p_income']:.2f})"
      f"  clean {f['B']['clean']['partial_r_income']:+.3f}   raw r: trap {f['B']['trap']['raw_r']:.3f}, clean {f['B']['clean']['raw_r']:.3f}")
print("Task C  slope of error on growth:"
      f"  trap pooled {f['C']['trap']['pooled_slope']:+.3f}, within A {f['C']['trap']['within_A_slope']:+.3f},"
      f" within B {f['C']['trap']['within_B_slope']:+.3f}   clean within A/B"
      f" {f['C']['clean']['within_A_slope']:+.3f}/{f['C']['clean']['within_B_slope']:+.3f}")
print("Task C  growth ranges, trap:  A", [round(x, 2) for x in f["C"]["trap"]["growth_range_A"]],
      " B", [round(x, 2) for x in f["C"]["trap"]["growth_range_B"]])
if bad:
    print(f"\nMISMATCH with answer_keys/verification.json: {bad}")
    sys.exit(1)
n = sum(len(key[t][v]) for t in "ABC" for v in ("trap", "clean"))
print(f"\nAll {n} answer-key numbers reproduced from data/.")
