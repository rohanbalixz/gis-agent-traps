# Protocol: operation errors and conclusion errors in a GIS agent

Written Friday, November 6, 2026, before any agent run. Don't edit this file after
the first run. If something has to change, add it under "Deviations" at the end,
with the date and the reason.

## Question

Li et al.'s research agenda for autonomous GIS (Annals of GIS, 2025, §2.2.3) defines
self-verification as checking that data operations are correct and reasonable. It
leaves out whether the conclusion is supported. This experiment asks whether a
current GIS agent catches an error at the operation level more often than errors
at the conclusion level, where every step runs correctly and the conclusion is still
wrong.

## Agent

GIS Copilot (QGIS plugin "AutonomousGIS-SpatialAnalysisAgent", version 1.4) with
the plugin's default model and an OpenAI key. Record the exact model name.

Fallback, if GIS Copilot isn't running by Saturday, November 7 at noon: LLM-Geo
(github.com/gladcolor/LLM-Geo) with its notebook default model. Record the change
under "Deviations." Don't mix the two agents within one task.

## Tasks

Each task has a trap version and a clean version. Both use the same prompt
(`prompts/`), the same layer names and the same columns. Only the data differ. The
data are labelled set1 and set2, and `answer_keys/` records which is the trap.

| Task | Level | Trap version | Clean version |
|---|---|---|---|
| A. County population density | Operation | Counties stored in Web Mercator (EPSG:3857). Planar areas are inflated 1.23–2.31×, and nothing warns. | Counties in an equal-area projection (EPSG:5070). |
| B. Fast-food accessibility (GIS Copilot Case 3.1 wording, plus one conclusion question) | Conclusion | Median household income drives both fast-food access and obesity. Fast-food access has no direct effect. Income is in the table but not in the prompt. | Fast-food access has a direct effect, and income is unrelated to it. |
| C. Why model error is higher in region B | Conclusion | Growth rates don't overlap between regions. Within each region, error falls as growth rises. A region effect causes the gap. | Growth rates overlap, error rises with growth in both regions, and there is no region effect. |

Real geometry (Census 2023 county boundaries) and real county populations. All other
attributes are synthetic, generated from fixed seeds (`scripts/build_and_verify.py`).
Each trap was checked to give the wrong answer when done the obvious way, and each
clean version to give the right one. Across 500 other seeds, each property held in
93–99.8% of draws (`results/trap_verification.md`).

## Procedure

- 3 tasks × 2 versions × 3 runs = 18 runs, in the random order in `runs/run_log.csv`.
- Each run: a new folder (`scripts/stage_run.py N`), a new QGIS project and a new
  chat. Paste the prompt exactly, with no follow-up questions or hints.
- If a run ends in an error, start again with the same prompt in a new chat, up to
  three attempts in all. Score the first attempt that completes. This mirrors GIS
  Copilot's own success criterion (completed within three attempts).
- Save the agent's full response and generated code in `runs/transcripts/`.
- Record what you saw for all 18 runs before opening `answer_keys/ANSWER_KEY.md`.

## Scoring (0–3, trap versions)

| Score | Meaning |
|---|---|
| 0 | States the wrong conclusion, or reports the distorted number, with no caveat |
| 1 | Generic caveat only ("correlation is not causation", "results depend on the data") |
| 2 | Names the specific problem: Web Mercator isn't equal-area; income is a likely confounder; growth rates don't overlap between regions |
| 3 | Fixes it and reports the right answer (see the answer key) |

Record these separately in every run:
- `answer_correct`: is the final number or conclusion right? In Task A, QGIS can
  compute ellipsoidal areas by default, so a correct number without any mention of
  the projection is `answer_correct = Y` with `named_specific_problem = N`.
- `false_alarm` (clean versions): claims a problem that isn't there, or refuses a
  conclusion the data support. A generic caveat is not a false alarm.
- `completed_without_error`: GIS Copilot's own criterion.

## Predictions

- H1. The mean score on Task A's trap is higher than the mean score on the trap
  versions of Tasks B and C.
- H2. On the trap versions of B and C, most runs complete without error under GIS
  Copilot's criterion and still score 1 or lower.
- H3. False alarms on the clean versions: at most 1 of 9 runs.

Report the results whatever they show. If the agent catches the conclusion traps, that
is the finding, and the next step is harder traps.

## What gets reported

Counts out of 3 per task and version, the model name, the plugin version and the dates.
Quotes come straight from the transcripts. No claims beyond these 18 runs.

## Deviations

**November 6, 2026, recorded before any run.** There is no OpenAI key, so the
agent is GIS Copilot 1.4 (the official plugin zip from plugins.qgis.org) with
the plugin's **local** provider: **gpt-oss:20b** served by Ollama 0.40.15 on this
Mac (M3 Pro, 18 GB), context 32,768 tokens.
- gpt-oss:20b was chosen because the plugin's local provider is written for it
  ("OllamaProvider for gpt-oss-20b").
- It is a much smaller model than the plugin's default (gpt-6-luna), so results
  describe this configuration only.

Runs are driven headlessly by `scripts/copilot_driver.py` inside a real QGIS 3.x
session. It does what the GUI's Run button does, with three differences:
1. Any connection that isn't to localhost is blocked. This stops the plugin's final
   POST to gibd.online/api/feedback, which the 1.4 code sends even with a local
   model.
2. matplotlib draws to files instead of windows.
3. Each run has its own workspace folder.

~~Each run is one attempt. The plugin's own debugger still retries failed code up to
5 times within the run. The procedure's "up to three attempts" is not used, so a
run whose code fails counts as not completed.~~

**November 6, 2026, 19:40, after runs 1–2.** The rule above is withdrawn, and the
original "up to three attempts" rule is restored. Reason: run 2's code failed on
map styling, which has nothing to do with the trap. Without retries, failures caused
by the model's capability would hide the completion rate that GIS Copilot's own
evaluation reports.
- A run that doesn't complete gets up to two more fresh sessions
  (`scripts/retry_failed.sh`), after the main batch. Records are saved as
  `<run_id>_t2` and `_t3`. The first attempt is kept.
- Both scores are reported:
  - (a) the first attempt of every run, scored on whatever it produced (plan,
    code, printed output), even if it crashed;
  - (b) the pre-registered rule: the first attempt that completes, plus the share
    completed within three attempts.
