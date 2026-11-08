#!/usr/bin/env python3
"""Build the six trap/clean datasets, then verify each trap from the saved files.

Usage:
  python build_and_verify.py --counties-shp cb_2023_us_county_500k.shp \
      --popest-csv co-est2023-alldata.csv --kit-dir ../

Inputs (public, downloaded separately; see README):
  Census cartographic boundary counties 2023 (1:500k)
  Census Vintage 2023 county population estimates

Everything synthetic is generated from MASTER_SEED, so reruns are identical.
"""
import argparse
import csv
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Geod
from scipy import stats
from shapely import contains_xy

MASTER_SEED = 20261107
NON_CONUS = {"02", "15", "60", "66", "69", "72", "78"}
DENSITY_THRESHOLD = 100.0  # people per km2
N_ROBUST = 500


# ---------------------------------------------------------------- helpers

def ols(y, X_cols, names):
    """OLS with intercept. Returns dict name -> (coef, se, p)."""
    y = np.asarray(y, float)
    X = np.column_stack([np.ones(len(y))] + [np.asarray(c, float) for c in X_cols])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    df = len(y) - X.shape[1]
    sigma2 = resid @ resid / df
    cov = sigma2 * np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(cov))
    t = beta / se
    p = 2 * stats.t.sf(np.abs(t), df)
    out = {"intercept": (beta[0], se[0], p[0])}
    for i, n in enumerate(names, start=1):
        out[n] = (beta[i], se[i], p[i])
    return out


def partial_corr(x, y, z):
    """Pearson correlation of x and y after removing a linear effect of z."""
    Z = np.column_stack([np.ones(len(z)), z])
    rx = x - Z @ np.linalg.lstsq(Z, x, rcond=None)[0]
    ry = y - Z @ np.linalg.lstsq(Z, y, rcond=None)[0]
    r = np.corrcoef(rx, ry)[0, 1]
    df = len(x) - 3
    t = r * np.sqrt(df / (1 - r * r))
    p = 2 * stats.t.sf(abs(t), df)
    return r, p


def geodesic_km2(gdf):
    geod = Geod(ellps="GRS80")
    g = gdf.to_crs(4269).geometry
    return np.array([abs(geod.geometry_area_perimeter(geom)[0]) / 1e6 for geom in g])


def write_layer(gdf, path, layer):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    gdf.to_file(path, layer=layer, driver="GPKG")


# ---------------------------------------------------------------- base data

def load_counties(shp, popcsv):
    g = gpd.read_file(shp)
    g = g[~g["STATEFP"].isin(NON_CONUS)].copy()
    pop = pd.read_csv(popcsv, dtype=str, encoding="latin-1")
    pop = pop[pop["SUMLEV"] == "050"].copy()
    pop["GEOID"] = pop["STATE"].str.zfill(2) + pop["COUNTY"].str.zfill(3)
    pop["POP2023"] = pop["POPESTIMATE2023"].astype(int)
    m = g.merge(pop[["GEOID", "POP2023"]], on="GEOID", how="left")
    missing = m["POP2023"].isna().sum()
    if missing:
        raise SystemExit(f"{missing} counties without population: "
                         f"{m.loc[m.POP2023.isna(), 'GEOID'].tolist()[:10]}")
    m["POP2023"] = m["POP2023"].astype(int)
    m = m[["GEOID", "NAME", "STATE_NAME", "POP2023", "geometry"]]
    return m.sort_values("GEOID").reset_index(drop=True)


# ---------------------------------------------------------------- generators

def gen_task_b(pop, version, rep):
    """County attributes for the fast-food task.

    trap : income drives both fast-food access and obesity; no direct effect.
    clean: fast-food access has a direct effect; income affects obesity only.
    """
    # All relationships are linear in the observed income column, so a linear
    # adjustment for income is enough to remove the confounding in the trap.
    n = len(pop)
    rng = np.random.default_rng([MASTER_SEED, 2, rep, 1])
    z_inc = rng.standard_normal(n)
    pct65 = np.clip(20 + 3 * rng.standard_normal(n), 12, 32).round(1)
    med_inc = (65000 + 14000 * z_inc).round(-2).astype(int)
    vr = np.random.default_rng([MASTER_SEED, 2, rep, 2 if version == "trap" else 3])
    if version == "trap":
        rate = 6.0 - 1.8 * z_inc            # restaurants per 10k people
        obesity = 32 - 2.0 * z_inc + vr.normal(0, 2.0, n)
    else:
        z_ff = vr.standard_normal(n)
        rate = 6.0 + 1.8 * z_ff
        obesity = 32 + 1.6 * z_ff - 1.5 * z_inc + vr.normal(0, 1.5, n)
    rate = np.clip(rate, 0.6, None)
    counts = vr.poisson(np.asarray(pop) / 1e4 * rate)
    return {"MED_HH_INC": med_inc, "PCT_65PLUS": pct65,
            "OBESITY": obesity.round(1), "counts": counts, "_vr": vr}


def gen_task_c(version, rep):
    """City table for the cross-region error task.

    trap : growth rates do not overlap between regions; within each region
           more growth means LOWER error; the gap comes from a region effect.
    clean: growth overlaps; error rises with growth in both regions; no
           region effect.
    """
    nA, nB = 30, 14
    rng = np.random.default_rng([MASTER_SEED, 3, rep, 2 if version == "trap" else 3])
    lonA, latA = rng.uniform(-95, -82, nA), rng.uniform(36, 46, nA)
    lonB, latB = rng.uniform(-115, -104, nB), rng.uniform(31, 37, nB)
    ndvi = np.clip(rng.normal(0.42, 0.08, nA + nB), 0.1, 0.8).round(3)
    popd = np.concatenate([rng.lognormal(7.2, 0.5, nA),
                           rng.lognormal(7.6, 0.5, nB)]).round(0).astype(int)
    if version == "trap":
        g = np.concatenate([rng.uniform(0.5, 2.5, nA), rng.uniform(3.5, 6.0, nB)])
        isB = np.r_[np.zeros(nA), np.ones(nB)]
        err = 0.45 - 0.04 * (g - 2) + 0.25 * isB + rng.normal(0, 0.03, nA + nB)
    else:
        g = np.concatenate([rng.uniform(0.5, 4.0, nA), rng.uniform(2.0, 6.0, nB)])
        err = 0.30 + 0.05 * g + rng.normal(0, 0.03, nA + nB)
    return {
        "CITY_ID": [f"A{i + 1:02d}" for i in range(nA)] + [f"B{i + 1:02d}" for i in range(nB)],
        "REGION": ["A"] * nA + ["B"] * nB,
        "ERROR": np.clip(err, 0, 1).round(3),
        "GROWTH": g.round(2),
        "NDVI": ndvi,
        "POP_DENS": popd,
        "lon": np.r_[lonA, lonB], "lat": np.r_[latA, latB],
    }


def sample_points(polys_proj, counts, rng):
    xs, ys, owner = [], [], []
    for geom, k, gid in zip(polys_proj.geometry, counts, polys_proj["GEOID"]):
        if k == 0:
            continue
        minx, miny, maxx, maxy = geom.bounds
        got_x, got_y = [], []
        while len(got_x) < k:
            bx = rng.uniform(minx, maxx, 4 * k + 16)
            by = rng.uniform(miny, maxy, 4 * k + 16)
            keep = contains_xy(geom, bx, by)
            got_x.extend(bx[keep]); got_y.extend(by[keep])
        xs.extend(got_x[:k]); ys.extend(got_y[:k]); owner.extend([gid] * k)
    return np.array(xs), np.array(ys), owner


# ---------------------------------------------------------------- build

def build(counties, data_dir, sets):
    # Task A: same counties, different CRS.
    a = counties.copy()
    write_layer(a.to_crs(3857), data_dir / "task_A" / sets["A"]["trap"] / "counties.gpkg", "counties")
    write_layer(a.to_crs(5070), data_dir / "task_A" / sets["A"]["clean"] / "counties.gpkg", "counties")

    # Task B: Pennsylvania counties + restaurant points.
    pa = counties[counties["GEOID"].str.startswith("42")].to_crs(4326).reset_index(drop=True)
    pa = pa[["GEOID", "NAME", "POP2023", "geometry"]]
    pa_proj = pa.to_crs(5070)
    for version in ("trap", "clean"):
        att = gen_task_b(pa["POP2023"].values, version, rep=0)
        out = pa.copy()
        out.insert(3, "MED_HH_INC", att["MED_HH_INC"])
        out.insert(4, "PCT_65PLUS", att["PCT_65PLUS"])
        out.insert(5, "OBESITY", att["OBESITY"])
        x, y, _ = sample_points(pa_proj, att["counts"], att["_vr"])
        order = att["_vr"].permutation(len(x))  # shuffle so IDs don't reveal county
        pts = gpd.GeoDataFrame({"REST_ID": [f"R{i + 1:05d}" for i in range(len(x))]},
                               geometry=gpd.points_from_xy(x[order], y[order]), crs=5070).to_crs(4326)
        d = data_dir / "task_B" / sets["B"][version]
        write_layer(out, d / "pa_counties.gpkg", "pa_counties")
        write_layer(pts, d / "fast_food_restaurants.gpkg", "fast_food_restaurants")

    # Task C: city table.
    for version in ("trap", "clean"):
        c = gen_task_c(version, rep=0)
        gdf = gpd.GeoDataFrame({k: c[k] for k in ("CITY_ID", "REGION", "ERROR", "GROWTH", "NDVI", "POP_DENS")},
                               geometry=gpd.points_from_xy(c["lon"], c["lat"]), crs=4326)
        write_layer(gdf, data_dir / "task_C" / sets["C"][version] / "cities.gpkg", "cities")


# ---------------------------------------------------------------- verify

def verify_a(path):
    g = gpd.read_file(path)
    planar = g.geometry.area.values / 1e6
    geo = geodesic_km2(g)
    dens_planar = g["POP2023"].values / planar
    dens_true = g["POP2023"].values / geo
    return {
        "crs": g.crs.to_string(),
        "n_counties": len(g),
        "count_above_planar": int((dens_planar > DENSITY_THRESHOLD).sum()),
        "count_above_true": int((dens_true > DENSITY_THRESHOLD).sum()),
        "median_density_planar": float(np.median(dens_planar)),
        "median_density_true": float(np.median(dens_true)),
        "area_ratio_min": float((planar / geo).min()),
        "area_ratio_max": float((planar / geo).max()),
        "top10_planar": g.assign(d=dens_planar).nlargest(10, "d")["NAME"].tolist(),
        "top10_true": g.assign(d=dens_true).nlargest(10, "d")["NAME"].tolist(),
    }


def score_b(pop, counts, inc, ob):
    score = counts / pop * 1e4
    r, p = stats.pearsonr(score, ob)
    pr, pp = partial_corr(score, ob, inc)
    m1 = ols(ob, [score], ["score"])
    m2 = ols(ob, [score, inc / 1000], ["score", "inc_k"])
    return {"raw_r": r, "raw_p": p, "partial_r_income": pr, "partial_p_income": pp,
            "slope_unadjusted": m1["score"][0], "slope_unadjusted_p": m1["score"][2],
            "slope_adjusted": m2["score"][0], "slope_adjusted_p": m2["score"][2]}


def verify_b(dirpath):
    c = gpd.read_file(dirpath / "pa_counties.gpkg")
    pts = gpd.read_file(dirpath / "fast_food_restaurants.gpkg")
    j = gpd.sjoin(pts, c[["GEOID", "geometry"]], predicate="within", how="left")
    counts = j.groupby("GEOID").size().reindex(c["GEOID"], fill_value=0).values
    res = score_b(c["POP2023"].values, counts, c["MED_HH_INC"].values, c["OBESITY"].values)
    res["n_counties"] = len(c)
    res["n_restaurants"] = len(pts)
    res["unjoined_points"] = int(j["GEOID"].isna().sum())
    res["corr_score_income"] = float(np.corrcoef(counts / c["POP2023"].values, c["MED_HH_INC"].values)[0, 1])
    return res


def stats_c(region, err, g):
    region = np.asarray(region)
    isB = (region == "B").astype(float)
    pooled = ols(err, [g], ["growth"])
    adj = ols(err, [g, isB], ["growth", "regionB"])
    wa = ols(err[region == "A"], [g[region == "A"]], ["growth"])
    wb = ols(err[region == "B"], [g[region == "B"]], ["growth"])
    return {"pooled_slope": pooled["growth"][0], "pooled_p": pooled["growth"][2],
            "within_A_slope": wa["growth"][0], "within_A_p": wa["growth"][2],
            "within_B_slope": wb["growth"][0], "within_B_p": wb["growth"][2],
            "adjusted_growth_slope": adj["growth"][0], "adjusted_regionB": adj["regionB"][0],
            "adjusted_regionB_p": adj["regionB"][2],
            "growth_range_A": [float(g[region == "A"].min()), float(g[region == "A"].max())],
            "growth_range_B": [float(g[region == "B"].min()), float(g[region == "B"].max())],
            "mean_error_A": float(err[region == "A"].mean()),
            "mean_error_B": float(err[region == "B"].mean())}


def verify_c(path):
    g = gpd.read_file(path)
    return stats_c(g["REGION"].values, g["ERROR"].values, g["GROWTH"].values)


def robustness(pa_pop):
    out = {}
    for version in ("trap", "clean"):
        ok = 0
        for rep in range(1, N_ROBUST + 1):
            att = gen_task_b(pa_pop, version, rep)
            s = score_b(pa_pop, att["counts"], att["MED_HH_INC"], att["OBESITY"])
            if version == "trap":
                ok += (s["raw_p"] < 0.01) and (s["partial_p_income"] > 0.05)
            else:
                ok += (s["raw_p"] < 0.01) and (s["partial_p_income"] < 0.01)
        out[f"B_{version}"] = ok / N_ROBUST
    for version in ("trap", "clean"):
        ok = 0
        for rep in range(1, N_ROBUST + 1):
            c = gen_task_c(version, rep)
            s = stats_c(np.array(c["REGION"]), c["ERROR"], c["GROWTH"])
            if version == "trap":
                ok += (s["pooled_slope"] > 0 and s["pooled_p"] < 0.01
                       and s["within_A_slope"] < 0 and s["within_B_slope"] < 0)
            else:
                ok += (s["pooled_slope"] > 0 and s["pooled_p"] < 0.01
                       and s["within_A_slope"] > 0 and s["within_B_slope"] > 0
                       and s["adjusted_regionB_p"] > 0.05)
        out[f"C_{version}"] = ok / N_ROBUST
    return out


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--counties-shp", required=True)
    ap.add_argument("--popest-csv", required=True)
    ap.add_argument("--kit-dir", required=True)
    args = ap.parse_args()
    kit = Path(args.kit_dir).resolve()
    data_dir = kit / "data"

    # Blind the set labels: per task, which of set1/set2 is the trap.
    rb = np.random.default_rng([MASTER_SEED, 99])
    sets = {}
    for t in ("A", "B", "C"):
        order = rb.permutation(["trap", "clean"])
        sets[t] = {order[0]: "set1", order[1]: "set2"}

    counties = load_counties(args.counties_shp, args.popest_csv)
    build(counties, data_dir, sets)

    res = {"master_seed": MASTER_SEED, "sets": sets, "A": {}, "B": {}, "C": {}}
    for v in ("trap", "clean"):
        res["A"][v] = verify_a(data_dir / "task_A" / sets["A"][v] / "counties.gpkg")
        res["B"][v] = verify_b(data_dir / "task_B" / sets["B"][v])
        res["C"][v] = verify_c(data_dir / "task_C" / sets["C"][v] / "cities.gpkg")
    pa_pop = counties.loc[counties["GEOID"].str.startswith("42"), "POP2023"].values
    res["robustness_share_of_500_seeds"] = robustness(pa_pop)

    (kit / "answer_keys").mkdir(exist_ok=True)
    with open(kit / "answer_keys" / "verification.json", "w") as f:
        json.dump(res, f, indent=2, default=float)

    # Randomised run order for the 18 runs.
    rr = np.random.default_rng([MASTER_SEED, 7])
    runs = [(t, s, k) for t in ("A", "B", "C") for s in ("set1", "set2") for k in (1, 2, 3)]
    runs = [runs[i] for i in rr.permutation(len(runs))]
    cols = ["run_order", "run_id", "task", "data_set", "agent", "agent_version", "model",
            "started_et", "completed_without_error", "attempts_used", "final_answer",
            "area_method_task_A", "generic_caveat", "named_specific_problem",
            "fixed_and_correct", "answer_correct", "false_alarm", "score_0_3",
            "notes", "transcript_file"]
    log = kit / "runs" / "run_log.csv"
    if log.exists():
        # Never overwrite a log that may hold recorded runs and scores.
        print(f"{log} already exists; left unchanged.")
        print(json.dumps(res, indent=2, default=lambda x: round(float(x), 4)))
        return
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for i, (t, s, k) in enumerate(runs, start=1):
            rid = f"{t}-{s}-r{k}"
            w.writerow([i, rid, t, s] + [""] * (len(cols) - 5) + [f"transcripts/{rid}.md"])

    print(json.dumps(res, indent=2, default=lambda x: round(float(x), 4)))


if __name__ == "__main__":
    main()
