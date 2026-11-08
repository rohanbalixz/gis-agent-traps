# Common tasks. PY must have the packages in requirements.txt.
PY ?= python3

.PHONY: verify figure summary runs retries

verify:   ## recompute every answer-key number from data/ (no QGIS needed)
	$(PY) scripts/verify_traps.py

figure:   ## redraw results/figures/ from runs/run_log.csv
	$(PY) scripts/make_figure.py

summary:  ## print each run's status, flags and output
	python3 scripts/summarize_runs.py

runs:     ## rerun all 18 runs (needs QGIS, Ollama and the plugin; see docs/reproduce.md)
	zsh scripts/run_local.sh 1 18

retries:  ## attempts 2 and 3 for runs that didn't complete
	zsh scripts/retry_failed.sh
