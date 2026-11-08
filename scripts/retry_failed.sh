#!/bin/zsh
# Retry runs that did not complete, per the protocol's "up to three attempts" rule.
# Each retry is a fresh QGIS session with a fresh copy of the run's data.
# Records are saved as <run_id>_t2 and <run_id>_t3; the first attempt is never
# overwritten. A run stops retrying as soon as one attempt completes.
#
#   scripts/retry_failed.sh

set -u
KIT="${0:A:h:h}"
CONDA="$HOME/miniforge3/bin/conda"
PROFILES="$HOME/gis_work/qgis_profiles"
export TRAP_KIT="$KIT" TRAP_PLUGIN_DIR="$PROFILES/profiles/default/python/plugins/SpatialAnalysisAgent-master"
export TRAP_MODEL="${TRAP_MODEL:-gpt-oss:20b}" TRAP_BASE_URL="${TRAP_BASE_URL:-http://127.0.0.1:11434/v1}"
export MPLBACKEND=Agg
T="$KIT/runs/transcripts"

st() { /usr/bin/python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['status'])" "$1" 2>/dev/null; }

/usr/bin/python3 -c "
import csv,sys
for r in csv.DictReader(open(sys.argv[1])): print(r['run_order'], r['run_id'], r['task'], r['data_set'])
" "$KIT/runs/run_log.csv" | while read N RID TASK SET; do
  [ -f "$T/$RID.json" ] || continue
  [ "$(st "$T/$RID.json")" = "completed" ] && continue
  for TRY in 2 3; do
    PREV=$([ $TRY -eq 2 ] && echo "$T/$RID.json" || echo "$T/${RID}_t2.json")
    [ -f "$PREV" ] && [ "$(st "$PREV")" = "completed" ] && break
    [ -f "$T/${RID}_t$TRY.json" ] && continue
    RD="$HOME/gis_work/run$(printf %02d "$N")_t$TRY"
    mkdir -p "$RD"
    for f in "$KIT/data/task_$TASK/$SET/"*.gpkg; do cp "$f" "$RD/"; done
    export TRAP_RUN_DIR="$RD" TRAP_RUN_ID="${RID}_t$TRY" TRAP_TASK_FILE="$KIT/prompts/task_$TASK.txt" TRAP_OUT_DIR="$T"
    echo "[$(date +%H:%M:%S)] start ${RID}_t$TRY"
    "$CONDA" run -n qgis --no-capture-output qgis --profiles-path "$PROFILES" --nologo \
        --noversioncheck --code "$KIT/scripts/copilot_driver.py" > "$T/${RID}_t$TRY.qgis_console.txt" 2>&1 < /dev/null
    echo "[$(date +%H:%M:%S)] end   ${RID}_t$TRY  status=$(st "$T/${RID}_t$TRY.json")"
  done
done
