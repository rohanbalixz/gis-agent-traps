# Methods

Design, setup, data and answer key. The pre-registered protocol is [`../PROTOCOL.md`](../PROTOCOL.md); results are in [`results.md`](results.md).

## 1. Question and design

The full protocol is in `PROTOCOL.md`. It was written before any run and hasn't been
edited since, except for the dated entries under "Deviations".

**Question.** Li et al.'s research agenda for autonomous GIS (Annals of GIS, 2025,
§2.2.3) defines self-verification as checking that data operations are correct and
reasonable. Whether the conclusion is supported is left out. Does a current GIS agent
catch an operation-level error more often than a conclusion-level one?

**Design.**
- 3 tasks × 2 versions × 3 runs = 18 runs, in the randomized order in
  `runs/run_log.csv`.
- Both versions of a task use the same prompt, layer names and columns. Only the data
  differ.
- The data folders are labelled `set1` and `set2`, so neither the agent nor the person
  running it sees which is the trap.
- Each run gets a neutral folder (`~/gis_work/runNN`), so no file path contains "trap"
  or "answer".

| Task | Level | Trap version | Clean version |
|---|---|---|---|
| A. County population density | Operation | Counties stored in Web Mercator (EPSG:3857). Planar areas are inflated 1.23–2.31×, and nothing warns about it. | Counties in an equal-area projection (EPSG:5070). |
| B. Fast-food accessibility and obesity (GIS Copilot Case 3.1 wording, plus one conclusion question) | Conclusion | Median household income drives both fast-food access and obesity, and access has no direct effect. Income is in the table but not in the prompt. | Access has a direct effect, and income is unrelated to it. |
| C. Why model error is higher in region B | Conclusion | Growth rates don't overlap between regions. Within each region, error falls as growth rises. A region effect causes the gap. | Growth rates overlap, error rises with growth in both regions, and there is no region effect. |

**Scoring (trap versions).**

| Score | Meaning |
|---|---|
| 0 | States the wrong conclusion, or reports the distorted number, with no caveat |
| 1 | Generic caveat only ("correlation is not causation") |
| 2 | Names the specific problem: Web Mercator isn't equal-area; income is a likely confounder; growth rates don't overlap |
| 3 | Fixes it and reports the right answer |

These fields are recorded separately for every run in `runs/run_log.csv`:
- `completed_without_error` (GIS Copilot's own criterion)
- `answer_correct`
- `false_alarm` (clean versions): claiming a problem that isn't there, or refusing a
  conclusion the data support. A generic caveat is not a false alarm.


## 2. Setup that was actually used

### Software and hardware

| Component | Version or detail |
|---|---|
| Agent | GIS Copilot, QGIS plugin "AutonomousGIS-SpatialAnalysisAgent" 1.4, the official zip from plugins.qgis.org |
| Model | gpt-oss:20b (about 12 GB), through the plugin's local provider at `http://127.0.0.1:11434/v1` |
| Model server | Ollama 0.40.15. Context 32,768 tokens, flash attention on, q8_0 KV cache. Fully on the GPU. |
| QGIS | 3.44.14 "Solothurn", Qt 5, Python 3.12.16, from conda-forge (env `qgis`, Miniforge) |
| Machine | Apple M3 Pro, 18 GB, macOS 27.0.1 |

Why gpt-oss:20b:
- There was no OpenAI key, and none was to be used.
- The plugin's local provider is written for this model ("OllamaProvider for
  gpt-oss-20b").
- It is much smaller than the plugin's default model, so the results describe this
  configuration only.

### The headless harness

`scripts/copilot_driver.py` runs inside a real QGIS session (`qgis --code`). It does
what the GUI's Run button does: it executes the plugin's
`SpatialAnalysisAgent_MyScript.py` with the same variables the dock widget passes (task,
data paths, workspace, model name, `is_review=False`, `reasoning_effort_value='medium'`).
The plugin's own debugger then retries failed code up to 5 times within the attempt.

It differs from clicking Run in four ways:
1. **Non-local network calls are blocked and logged.** The driver patches
   `socket.getaddrinfo`, `socket.socket.connect` and `requests.post`. This stops the
   plugin's final POST to gibd.online ([results, section 4.1](results.md#41-the-plugins-end-of-run-request)).
2. **matplotlib draws to files** (the Agg backend) instead of windows.
3. **Each run has its own workspace folder.**
4. **The plugin's config is written before each run.** The config gets an empty
   `[API_Key]` section, which the GUI creates the first time it opens, and the
   `[LocalModel]` settings.

Per attempt, the driver writes these files to `runs/transcripts/`:
- `<run_id>.json`: the full record, including plan, selected tools, final code, program
  output, every code error with its traceback, and the blocked network calls.
- `<run_id>.md`: a readable version.
- `.log` and `.qgis_console.txt`: the console logs, moved afterwards to `runs/raw_logs/`.

There is also a 75-minute timeout. Its timer (`threading.Timer`, a monotonic clock)
pauses while the Mac sleeps, but the elapsed time in each record is wall-clock time.
That is why run 15's third attempt shows 208 minutes without timing out.

Map snapshots didn't save: only `_map.pgw` world files were written. The maps aren't
needed for scoring.

**Memory.**
- During run 8, the model server grew to about 17 GB and the Mac swapped heavily.
- From 21:22 on (run 9 onward, and all retries), a background loop unloaded the model
  each time a new run record appeared, so each attempt started with a fresh model load.
- The retries' elapsed times are inflated by swapping and by the Mac sleeping overnight.

### Smoke test

The smoke test asked: "How many features are in the layer "cities"? Print the number."
It used `scripts/run_local.sh smoke` on the Task C clean layer.

| Time | Result |
|---|---|
| 19:06 | Failed in 0.1 min. The plugin config had no `[API_Key]` section. The driver now writes an empty one. |
| 19:07 | Completed in 2.2 min and printed `44` (correct). |

### Deviations from the protocol (recorded in PROTOCOL.md)

1. **Before any run.** The planned agent was GIS Copilot with its default model and an
   OpenAI key. It was replaced by the local provider with gpt-oss:20b, driven headlessly
   as described above.
2. **19:40, after runs 1–2.** The first deviation had also set one attempt per run.
   That rule was withdrawn and the protocol's "up to three attempts" rule restored. Run 2
   had failed on map styling, which has nothing to do with the trap. Failed runs got up
   to two more fresh sessions after the main batch (`scripts/retry_failed.sh`). Both
   scoring rules (a) and (b) are reported.


## 3. Data, prompts and answer key

The geometry and populations are real: Census 2023 county boundaries
(cb_2023_us_county_500k) and Vintage 2023 county population estimates. Every other
attribute is synthetic, generated by `scripts/build_and_verify.py` from fixed seeds
(`MASTER_SEED = 20261107`).

### Prompts (verbatim, in `prompts/`)

**Task A.**

> The layer "counties" contains every county in the contiguous United States, with its
> 2023 population in the field POP2023. Calculate the population density of each county
> in people per square kilometre and show it on a map with graduated colours. Then tell
> me how many counties have a density above 100 people per square kilometre, and what
> the median county density is.

**Task B.**

> Could you analyze and visualize the fast food accessibility score for each county
> based on the number of fast food restaurants and population using a thematic map with
> blue graduated colors. Then, analyze the correlation between the county-level obesity
> rate and the fast food accessibility score by drawing a scatter plot with a regression
> line. In one sentence, what does this suggest about whether fast-food access affects
> obesity?

**Task C.**

> The layer "cities" has 44 cities. An urban-growth model was trained on the cities in
> region A (REGION = "A") and applied, without retraining, to the cities in region B.
> ERROR is the model's test error in each city (higher is worse). GROWTH is the city's
> annual built-up growth rate in percent per year, NDVI is its mean vegetation index,
> and POP_DENS is its population density in people per square kilometre. Map the error.
> Then use the covariates to explain why the error is higher in region B, and say which
> covariate is responsible.

### Datasets

| Task | Set | Role | Layer | Features | CRS | Fields |
|---|---|---|---|---|---|---|
| A | set1 | **trap** | counties | 3,109 | EPSG:3857 | GEOID, NAME, STATE_NAME, POP2023 |
| A | set2 | clean | counties | 3,109 | EPSG:5070 | same |
| B | set1 | clean | pa_counties + fast_food_restaurants | 67 + 7,510 | EPSG:4326 | GEOID, NAME, POP2023, MED_HH_INC, PCT_65PLUS, OBESITY / REST_ID |
| B | set2 | **trap** | pa_counties + fast_food_restaurants | 67 + 7,454 | EPSG:4326 | same |
| C | set1 | **trap** | cities | 44 (30 in A, 14 in B) | EPSG:4326 | CITY_ID, REGION, ERROR, GROWTH, NDVI, POP_DENS |
| C | set2 | clean | cities | 44 | EPSG:4326 | same |

### Answer key (from `answer_keys/ANSWER_KEY.md` and `verification.json`)

**Task A.**

| | Trap (set1, EPSG:3857) | Clean (set2, EPSG:5070) |
|---|---|---|
| Counties above 100/km², planar area in the file's CRS | **317** (wrong) | **464** (right) |
| Counties above 100/km², true (geodesic) area | 464 | 464 |
| Median density, planar | **10.6** (wrong) | **17.2** (right) |
| Median density, true | 17.2 | 17.2 |
| Planar ÷ true area | 1.23 (south Florida) to 2.31 (northern border) | 1.000 |

- **Correct answer:** 464 ± 2 counties and a median of 17.2 ± 0.2 people/km².
- **A score of 3** needs the right numbers plus a sign that the projection was handled:
  reprojecting, or choosing ellipsoidal area explicitly.
- **Which area functions are which:**
  - `$area` in the field calculator is ellipsoidal when the project has an ellipsoid
    set.
  - `area($geometry)` and PyQGIS `geometry().area()` are planar.

**Task B.** The accessibility score is restaurants per 10,000 residents. The
correlations don't depend on the units.

| | Trap (set2) | Clean (set1) |
|---|---|---|
| Raw r, score vs. obesity | 0.64 (p < 0.001) | 0.57 (p < 0.001) |
| r, score vs. income | −0.85 | 0.16 |
| Partial r, controlling for income | **−0.05 (p = 0.66)** | **0.69 (p < 0.001)** |
| Slope without income | 0.94 | 0.69 |
| Slope with income | **−0.10 (p = 0.66)** | **0.79 (p < 0.001)** |

The raw scatter plots look alike. Without income, the two versions can't be told
apart.
- **Trap:** the association is explained by income.
- **Clean:** the association survives adjusting for income. Flagging income as
  something to check is not a false alarm. Claiming that income explains the
  association is one.

**Task C.**

| | Trap (set1) | Clean (set2) |
|---|---|---|
| GROWTH range, region A | 0.60–2.28 | 0.54–3.99 |
| GROWTH range, region B | 3.66–5.98 (**no overlap**) | 2.07–5.80 (overlap 2.07–3.99) |
| Mean ERROR, A vs. B | 0.474 vs. 0.593 | 0.420 vs. 0.486 |
| Pooled slope, ERROR on GROWTH | **+0.025 (p < 0.001)** | +0.052 (p < 0.001) |
| Slope within region A | **−0.036 (p = 0.003)** | +0.051 (p < 0.001) |
| Slope within region B | **−0.054 (p = 0.001)** | +0.054 (p < 0.001) |
| Region B effect, adjusting for growth | **+0.28 (p < 0.001)** | −0.001 (p = 0.91) |

- **Trap:** growth can't be credited with the gap. The regions don't overlap in
  growth, and within each region error falls as growth rises. The gap goes with
  region, and NDVI and POP_DENS have no effect.
- **Clean:** higher growth explains the higher error in region B.

### Were the traps real? (`results/trap_verification.md`)

Every number was recomputed from the saved GeoPackages. Each trap gives the wrong
answer when done the obvious way, and each clean version gives the right one.

To check that this comes from the design rather than one lucky seed, Tasks B and C were
regenerated with 500 other seeds:

| Version | Property | Share of seeds where it holds |
|---|---|---|
| B trap | raw p < 0.01 and partial p > 0.05 | 93.2% |
| B clean | raw p < 0.01 and partial p < 0.01 | 97.0% |
| C trap | pooled slope > 0 (p < 0.01) and both within-region slopes < 0 | 99.8% |
| C clean | all slopes > 0, region effect p > 0.05 | 95.4% |

Task A has no randomness: Web Mercator inflates area by 1/cos²(latitude).

**Two bugs were caught while building, before any run:**
1. **Task B's partial correlation came out at 0.59 instead of about 0.**
   - Cause: the first version used log-scale income and an exponential fast-food rate,
     so a straight-line income adjustment left curvature behind.
   - Effect: an agent that adjusted correctly would have been penalised.
   - Fix: every relationship is now linear in the observed income column.
2. **Obesity came out constant in the Task B trap.**
   - Cause: numpy treats the seeds `[s, 2, 0]` and `[s, 2, 0, 0]` as identical, so the
     trap's obesity noise repeated the income draws exactly.
   - Fix: every random stream now has a distinct, nonzero final tag.


## 4. Timeline

| When (ET) | What |
|---|---|
| Nov 6, before the runs | Protocol written. Datasets built and verified, including the 500-seed check and the two build bugs fixed. |
| Nov 6, before the runs | Deviation recorded: local gpt-oss:20b instead of an OpenAI key, with the headless driver. |
| Nov 6, 19:06 | First smoke test failed: missing `[API_Key]` config section. |
| Nov 6, 19:07 | Second smoke test completed in 2.2 min (printed 44). |
| Nov 6, 19:10–22:22 | 18 first attempts. 13 completed. |
| Nov 6, 19:40 | Deviation recorded: the "up to three attempts" rule restored. |
| Nov 6, 22:39 – Nov 7, 04:30 | Retries of runs 2, 3, 6, 8 and 15. Four completed; run 15 failed all three attempts. |
| Nov 7 | Scoring under both rules. |
| Nov 8 | Score check: every quote matched against the records; judgment calls listed. Repository prepared. |
