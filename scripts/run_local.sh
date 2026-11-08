#!/bin/zsh
# Run GIS Copilot 1.4 headlessly against a local Ollama model.
#
#   scripts/run_local.sh smoke        one trivial request, to check the setup
#   scripts/run_local.sh 1 18         runs 1 to 18 from runs/run_log.csv
#   scripts/run_local.sh 5            run 5 only
#
# Needs: Ollama serving on 127.0.0.1:11434 with $TRAP_MODEL pulled, the conda env
# "qgis" (QGIS 3.x), and the official plugin unzipped into the run profile.
# QGIS windows open and close on screen while this runs.

set -u
KIT="${0:A:h:h}"
CONDA="$HOME/miniforge3/bin/conda"
PROFILES="$HOME/gis_work/qgis_profiles"
PLUGIN="$PROFILES/profiles/default/python/plugins/SpatialAnalysisAgent-master"
export TRAP_KIT="$KIT" TRAP_PLUGIN_DIR="$PLUGIN"
export TRAP_MODEL="${TRAP_MODEL:-gpt-oss:20b}" TRAP_BASE_URL="${TRAP_BASE_URL:-http://127.0.0.1:11434/v1}"
export MPLBACKEND=Agg

curl -s http://127.0.0.1:11434/api/version >/dev/null || { echo "Ollama is not running on 127.0.0.1:11434"; exit 1; }
[ -d "$PLUGIN" ] || { echo "Plugin not found at $PLUGIN"; exit 1; }

launch() {  # $1 run dir, $2 run id, $3 task file, $4 output dir
  export TRAP_RUN_DIR="$1" TRAP_RUN_ID="$2" TRAP_TASK_FILE="$3" TRAP_OUT_DIR="$4"
  echo "[$(date +%H:%M:%S)] start $2"
  "$CONDA" run -n qgis --no-capture-output qgis --profiles-path "$PROFILES" --nologo \
      --noversioncheck --code "$KIT/scripts/copilot_driver.py" > "$4/$2.qgis_console.txt" 2>&1
  local rc=$?
  local st="$(/usr/bin/python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['status'])" "$4/$2.json" 2>/dev/null)"
  echo "[$(date +%H:%M:%S)] end   $2  exit=$rc  status=${st:-no-record}"
}

if [ "${1:-}" = "smoke" ]; then
  D="$HOME/gis_work/smoke_$(date +%Y%m%d_%H%M%S)"; mkdir -p "$D"
  cp "$KIT/data/task_C/set2/cities.gpkg" "$D/"
  echo 'How many features are in the layer "cities"? Print the number.' > "$D/task.txt"
  launch "$D" smoke "$D/task.txt" "$D"
  echo "Smoke output: $D"
  exit 0
fi

FIRST="${1:?usage: run_local.sh smoke | FIRST [LAST]}"; LAST="${2:-$FIRST}"
for N in $(seq "$FIRST" "$LAST"); do
  ROW="$(/usr/bin/python3 -c "
import csv,sys
for r in csv.DictReader(open(sys.argv[1])):
    if int(r['run_order'])==int(sys.argv[2]): print(r['run_id'], r['task'])
" "$KIT/runs/run_log.csv" "$N")"
  RID="${ROW%% *}"; TASK="${ROW##* }"
  RD="$HOME/gis_work/run$(printf %02d "$N")"
  if [ -f "$KIT/runs/transcripts/$RID.json" ]; then echo "skip $RID (already has a record)"; continue; fi
  /usr/bin/python3 "$KIT/scripts/stage_run.py" "$N" > /dev/null || { echo "staging failed for run $N"; continue; }
  launch "$RD" "$RID" "$KIT/prompts/task_$TASK.txt" "$KIT/runs/transcripts"
done
