# Results

Every quote is copied from the run records in [`../runs/transcripts/`](../runs/transcripts/). Scores and observations per run are in [`../runs/run_log.csv`](../runs/run_log.csv). Methods are in [`methods.md`](methods.md).

## 1. Results by task

Quotes are copied from the run records in `runs/transcripts/`. A "t2" or "t3" means the
second or third attempt (section 2).

### Task A: county population density (trap = Web Mercator)

| Run | Version | Attempt | Status | Plan (quoted) or area method | Printed | Score (a) | Score (b) |
|---|---|---|---|---|---|---|---|
| 2 | trap | t1 | failed (styling: `setColorRamp`) | "Transform `counties` from EPSG:3857 to an equal‑area CRS (e.g., EPSG:5070) to ensure accurate area calculations." | "Count of counties with density > 100 people/km²: 464" (correct). No median, because of the crash. | **2** | |
| 2 | trap | t2 | completed | **No reprojection.** Plan: "Recalculate Geometry – Compute area of each county polygon in square kilometres." Area came from `native:exportaddgeometrycolumns` in EPSG:3857. | `3109` (a selection bug) and `10.550344`, **the trap median** | | **0** |
| 4 | trap | t1 | completed | "Reproject the `counties` layer to a projected CRS with units in meters (e.g., EPSG:5070) to enable accurate area calculation." Then `$area`. | Count 3109 (a selection bug); median 17.0 (true 17.2) | **2** | **2** |
| 6 | trap | t1 | failed (styling, then processing parameters) | "Transform *counties* from EPSG:3857 to a projected CRS suitable for area calculations (e.g., EPSG:5070)." | nothing | **2** | |
| 6 | trap | t2 | completed | "Reproject the *counties* layer from EPSG:3857 to an equal‑area CRS (e.g., EPSG:5070) to enable accurate area calculations". `native:reprojectlayer`, then `$area/1000000`. | "Number of high density counties: 464" and "Median population density (people/km²): 17.179". **Both correct.** | | **3** |
| 7 | clean | t1 | completed | `$area` in the layer's own EPSG:5070, with no reprojection (correct) | `3109`, `-1`, "No density values found." (code bugs) | no false alarm | same |
| 11 | clean | t1 | completed | `area($geometry)` in EPSG:5070, no reprojection | `0`, `nan` (code bugs) | no false alarm | same |
| 15 | clean | t1 | failed (styling) | geopandas `.area` in EPSG:5070 (`to_crs` only if not projected) | nothing | no false alarm | |
| 15 | clean | t2 | failed (processing parameters) | no reprojection | nothing | | |
| 15 | clean | t3 | failed (`QgsColor` undefined, `QVariant` division) | no reprojection | `3109` only | | not completed |

**Notes on Task A:**
- **Run 4's reason was wrong.** It reprojected "to enable accurate area calculation" in
  "units in meters", but Web Mercator is already in meters. The fix was right and the
  stated reason wasn't, so it scored 2.
- **The recurring count of 3109 is a bug.** `qgis:selectbyexpression` returns the input
  layer, and the code then counted every feature.
- **Plans across all attempts:**
  - Trap: 4 of 5 reprojected.
  - Clean: 0 of 5 reprojected, which is correct, since the layer was already equal-area.

### Task B: fast-food accessibility and obesity (trap = income drives both)

| Run | Version | Attempt | Status | Printed | Income used? | Score (a) | Score (b) |
|---|---|---|---|---|---|---|---|
| 5 | trap | t1 | completed, 0 code errors | "Correlation coefficient: 0.639" · "Higher fast‑food accessibility is associated with higher obesity rates." | No | 0 | 0 |
| 9 | trap | t1 | completed | "Correlation coefficient (Pearson r): nan" · "Higher fast‑food accessibility is not associated with higher obesity rates." | No | 0: a conclusion drawn from a NaN | 0 |
| 17 | trap | t1 | completed | "Correlation between obesity and accessibility: 0.639", with no conclusion sentence | No | 0 | 0 |
| 1 | clean | t1 | completed | A scatter plot only: no r and no conclusion | No | no false alarm | same |
| 14 | clean | t1 | completed | "Pearson correlation (AccScore vs OBESITY): 0.5669" (correct), with no conclusion | No | no false alarm | same |
| 8 | clean | t1 | failed after 66.8 min (join field, scatterplot tool, syntax) | nothing | No | no false alarm | |
| 8 | clean | t2 | completed in 3.7 min | A scatter plot only. The plan dropped the conclusion question. | No | | no false alarm |

**Notes on Task B:**
- **The trap's raw correlation was reproduced but never questioned.** Runs 5 and 17
  printed 0.639, which matches the key's raw r of 0.64. After adjusting for income, the
  correct value is r = −0.05 (p = 0.66).
- **The causal question never reached the analysis.** The prompt asks "what does this
  suggest about whether fast-food access affects obesity?" No plan kept "affects":
  - 3 rewrote it as an association question (runs 5, 9 and 8). For example, run 5:
    "Summarize in one sentence whether higher fast‑food accessibility is associated
    with higher obesity rates."
  - 3 dropped it (runs 1, 14 and 17). Run 8's second attempt dropped it too.
- **The conclusion sentence came from the sign of r.** Where one was printed, an if/else
  chose it, which is how run 9 printed "not associated" from a NaN.
- **Income was in front of the model every time.** The plugin's data overview listed
  every column with a sample value, including `MED_HH_INC`. It was used in 0 of 7
  attempts.

### Task C: why error is higher in region B (trap = no overlap in growth)

| Run | Version | Attempt | Status | Printed | Score (a) | Score (b) |
|---|---|---|---|---|---|---|
| 12 | trap | t1 | completed, 0 code errors | "GROWTH vs ERROR: r=0.640" (pooled). Within region B: "GROWTH vs ERROR: r=-0.778, p=1.060e-03". Then "Dominant covariate driving higher ERROR in Region B: GROWTH". | 0: its own within-region number contradicts its conclusion | 0 |
| 16 | trap | t1 | completed, 0 code errors | "Covariate most strongly correlated with ERROR: GROWTH (0.6396)" · "Likely driver of higher error in region B: GROWTH" | 0 | 0 |
| 3 | trap | t1 | failed (processing parameters) | nothing. The plan was "Model ERROR as a function of GROWTH, NDVI, and POP_DENS across all cities", a pooled model with no overlap check. | 0 | |
| 3 | trap | t2 | completed, 0 code errors | Mean ERROR: A 0.4737, B 0.5934 (matches the key). Region B correlations: GROWTH −0.778, NDVI 0.051, POP_DENS −0.253. Then "Dominant covariate explaining higher error in region B: GROWTH". | | 0 |
| 10 | clean | t1 | completed | Per-region slopes of +0.051 and +0.054 (match the key) · "Dominant covariate…: GROWTH" | correct | same |
| 18 | clean | t1 | completed | Region B: "GROWTH… r=0.947" · "Key covariate…: GROWTH" | correct | same |
| 13 | clean | t1 | completed | "Covariate with greatest difference: POP_DENS (difference: 257.0857)". It compared raw means across variables with different units. | wrong, but not a false alarm | same |

**Notes on Task C:**
- **The non-overlap was printed but not noticed.** Runs 12 and 16 printed GROWTH means
  of 1.4 for region A and 4.9 for region B, and the ranges don't overlap. No run
  compared them.
- **"Responsible" meant the largest |r|.** Every trap run picked the covariate with the
  largest absolute correlation. In runs 12 and 3, that was a negative within-region-B
  correlation: error falls as growth rises, the opposite of the conclusion drawn.


## 2. Retries

Script: `scripts/retry_failed.sh`, log: `runs/retry_20261106_2239.log`.
- Each retry was a fresh QGIS session with a fresh copy of the data.
- A run stopped retrying as soon as one attempt completed.
- First attempts were never overwritten.

| Run | Task, version | Attempt | Start–end | Elapsed | Status | Outcome |
|---|---|---|---|---|---|---|
| 2 | A trap | t2 | 22:39–23:24 | 44.3 min | completed | No reprojection; trap median 10.55. **Score 0** under (b). |
| 3 | C trap | t2 | 23:24–23:55 | 31.1 min | completed | Named GROWTH, no overlap check. Score 0. |
| 6 | A trap | t2 | 23:55–00:45 | 49.7 min | completed | Reprojected; 464 and 17.179, both correct. **Score 3.** |
| 8 | B clean | t2 | 00:45–00:49 | 3.7 min | completed | Scatter plot only; no false alarm. |
| 15 | A clean | t2 | 00:49–01:01 | 12.5 min | failed 5 times | Processing parameters. |
| 15 | A clean | t3 | 01:01–04:29 | 208.1 min* | failed 5 times | Styling and `QVariant` errors; printed `3109` only. |

\* Inflated by swapping and by the Mac sleeping overnight.

The two Task A trap retries went in opposite directions:
- **Run 6** failed with a correct plan and then succeeded with one.
- **Run 2** first reprojected and printed the right count, then on the retry, with the
  same prompt and the same data, skipped the reprojection and reported the trap answer.


## 3. Completion and code errors

| | First attempt | Within 3 attempts |
|---|---|---|
| Runs completed | 13 of 18 | 17 of 18 |
| Task A | 3 of 6 | 5 of 6 |
| Task B | 5 of 6 | 6 of 6 |
| Task C | 5 of 6 | 6 of 6 |

**Why the 5 first attempts failed:**

| Cause | Runs |
|---|---|
| Map styling: renderer methods QGIS doesn't have, such as `setColorRamp` | 2 and 15 |
| A styling error, then a processing-tool parameter error | 6 |
| Processing-tool parameters | 3 and 8 |

None of these involved a trap.

**All code errors.** Across the 24 attempts (18 first attempts and 6 retries), the
plugin's debugger caught 55 failed code executions. Grouped by keyword in the error
message (the total is exact; the split depends on the keywords chosen, and another
grouping gave 25, 21 and 9):

| Type | Count | Examples |
|---|---|---|
| Processing-tool parameters | 21 | "Unable to execute algorithm … Could not load source layer for INPUT_LAYER", "Incorrect parameter value for FIELD_NAME" |
| Styling, or Qt/QGIS names not imported | 20 | "'QgsGraduatedSymbolRenderer' object has no attribute 'setColorRamp'", "name 'QColor' is not defined", "cannot import name 'QgsRendererRangeList'" |
| Other | 14 | wrong argument types (`QgsVectorLayer(): argument 1 has unexpected type 'QgsVectorLayer'`), missing fields (`'POP_DENS'`, "GEOID does not exist"), a syntax error, `QVariant` division |

**Time per attempt.**
- The median first attempt took 6.6 minutes (range 3.9–66.8).
- The batch of 18 took 3 hours 12 minutes.

**Per-attempt record:**

| Attempt | Status | Elapsed (min) | Failed code executions | Last error |
|---|---|---|---|---|
| B-set1-r1 (run 1) | completed | 7.0 | 2 | `setColorRamp` |
| A-set1-r2 (run 2) | failed | 12.3 | 5 | `setColorRamp` |
| A-set1-r2_t2 | completed | 44.3 | 2 | `QgsVectorLayer()` argument type |
| C-set1-r2 (run 3) | failed | 10.0 | 5 | Unable to execute algorithm |
| C-set1-r2_t2 | completed | 31.1 | 0 | |
| A-set1-r3 (run 4) | completed | 11.5 | 3 | Unable to execute algorithm |
| B-set2-r1 (run 5) | completed | 4.1 | 0 | |
| A-set1-r1 (run 6) | failed | 10.8 | 5 | Unable to execute algorithm |
| A-set1-r1_t2 | completed | 49.7 | 2 | Unable to execute algorithm |
| A-set2-r1 (run 7) | completed | 10.1 | 4 | Unable to execute algorithm |
| B-set1-r3 (run 8) | failed | 66.8 | 5 | scatterplot tool traceback |
| B-set1-r3_t2 | completed | 3.7 | 0 | |
| B-set2-r2 (run 9) | completed | 8.9 | 2 | Unable to execute algorithm |
| C-set2-r2 (run 10) | completed | 5.4 | 1 | Unable to execute algorithm |
| A-set2-r2 (run 11) | completed | 4.6 | 1 | Unable to execute algorithm |
| C-set1-r1 (run 12) | completed | 3.9 | 0 | |
| C-set2-r1 (run 13) | completed | 4.4 | 0 | |
| B-set1-r2 (run 14) | completed | 5.6 | 1 | `QSize` not defined |
| A-set2-r3 (run 15) | failed | 8.5 | 5 | `setColorRamp` |
| A-set2-r3_t2 | failed | 12.5 | 5 | Unable to execute algorithm |
| A-set2-r3_t3 | failed | 208.1* | 5 | `QVariant` / `int` division |
| C-set1-r3 (run 16) | completed | 4.0 | 0 | |
| B-set2-r3 (run 17) | completed | 5.7 | 1 | `QColor` not defined |
| C-set2-r3 (run 18) | completed | 6.1 | 1 | `QgsRendererRangeList` import |

"Completed" is GIS Copilot's own criterion: the final code ran. A run can complete and
still print wrong numbers, as runs 7 and 11 did.


## 4. Other findings

### 4.1 The plugin's end-of-run request

At the end of every run, GIS Copilot 1.4 sends a request to the developers' server,
even when the model is local. The driver blocks it ([methods, section 2](methods.md#2-setup-that-was-actually-used)), so each run record
lists one blocked call. A related issue is being reported to the maintainers
privately, and details will be added here once they have had a chance to respond.

### 4.2 Code quality limits the numbers more than judgment does

- **Clean Task A:** the right projection decision in 5 of 5 attempts, and no correct
  count or median.
- **A count of 3109,** which is every county, was printed in 4 attempts: run 4, run 2
  t2, run 7 and run 15 t3.
- **Implication:** on this model, "did it get the number right?" mixes two failures. One
  is code that doesn't work. The other is a judgment the code never questions. The
  plan, code and printed output are therefore scored separately in the transcripts.

### 4.3 The agent's plan rewrites the question

In Task B, the plan stage turned "affects" into "is associated with", or dropped the
question. That happened before any code ran, so the conclusion never got checked: the
question that would have needed income was gone.

### 4.4 The same task gives different answers

Run 2's two attempts had the same prompt and the same data. One reprojected and one
didn't. That flip alone takes run 2 from 3 to 0, which moves a 3-run mean by a full
point.



## 5. Score check (November 8)

**Quotes.** Every quoted line of plan, code or printed output in these docs was matched by script against the JSON records and logs. All were found
verbatim. The only exceptions are an error message shown without its curly quotes
("GEOID does not exist") and text that isn't agent output (prompts, commands, rubric
wording).

**Scores that need no judgment:**
- Every Task B and C trap attempt scores 0 under any reading. None printed any caveat,
  so none can reach 1, and none mentioned income or overlap.
- The 0 false alarms hold under any reading. No clean attempt raised any concern.
- Run 2 t2 = 0: it reported the distorted median with no caveat.
- Run 6 t2 = 3: it reprojected and printed both correct numbers.

**Judgment calls (all in Task A), decided by Rohan Bali on November 8:**

| Attempt | First pass | Decision | Why |
|---|---|---|---|
| Run 2 t1 | 3 | **2** | Reprojected and printed the right count (464), but crashed before printing the median. The answer key requires "the right numbers", and only one of the two requested numbers was reported. |
| Run 4 t1 | 2 | **2** | Reprojected, which the key accepts as a sign the projection was handled, but gave the wrong reason ("units in meters"). The median (17.0) is right; the count (3109) is wrong because of an unrelated selection bug. |
| Run 6 t1 | 2 | **2** | The plan reprojects "from EPSG:3857 to a projected CRS suitable for area calculations", but no numbers were printed. |

**Sensitivity:**
- Task A mean: 2.00 under (a), first attempts (3, 2 and 2 would have given 2.33 before
  the decision); 1.67 under (b), the pre-registered rule. Any defensible reading of the
  three calls keeps (a) between 2.00 and 2.67 and (b) between 1.67 and 2.00.
- Tasks B and C: 0 in every reading.
- H1, H2 and H3 hold in every reading.
- The reprojection counts (2 of 3 runs under rule (b), 4 of 5 attempts) don't depend
  on these calls.

