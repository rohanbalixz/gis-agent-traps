# Reproducing everything

### Check the shipped data (about a minute)

```
pip install -r requirements.txt
python scripts/verify_traps.py        # or: make verify
```

This recomputes every answer-key number from `data/` and exits non-zero on any
mismatch.

### Rebuild the data and the answer key

```
pip install -r requirements.txt
curl -O https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip   # unzip
curl -O https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/counties/totals/co-est2023-alldata.csv
python scripts/build_and_verify.py --counties-shp cb_2023_us_county_500k.shp \
    --popest-csv co-est2023-alldata.csv --kit-dir .
```

The seeds are fixed (`MASTER_SEED = 20261107`), so a rebuild produces identical files.
If `runs/run_log.csv` already exists, the rebuild leaves it unchanged.

### Rerun the agent locally (as it was done here)

1. **Ollama.** Install it, then `ollama pull gpt-oss:20b`. Serve it with:
   ```
   OLLAMA_HOST=127.0.0.1:11434 OLLAMA_CONTEXT_LENGTH=32768 OLLAMA_FLASH_ATTENTION=1 \
   OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_KEEP_ALIVE=60m ollama serve
   ```
2. **QGIS 3.x on Qt 5.** The plugin needs PyQt5 and QGIS 3.99 or lower. Without a
   version cap, conda resolves QGIS 4 on Qt 6, which doesn't work.
   ```
   conda env create -f environment.yml      # or: conda create -n qgis -c conda-forge "qgis>=3.40,<4"
   ```
3. **The plugin.** Unzip the official GIS Copilot 1.4 zip into
   `~/gis_work/qgis_profiles/profiles/default/python/plugins/SpatialAnalysisAgent-master`.
4. **Run:**
   ```
   scripts/run_local.sh smoke      # one trivial request; should print 44
   scripts/run_local.sh 1 18       # all 18 runs in log order; skips runs that already have a record
   scripts/retry_failed.sh         # attempts 2 and 3 for runs that didn't complete
   python3 scripts/summarize_runs.py [--task A|B|C]
   python scripts/make_figure.py   # redraw results/figures/ from runs/run_log.csv
   ```
   - Optional settings: `TRAP_MODEL`, `TRAP_BASE_URL` and `TRAP_TIMEOUT_MIN` (default 75).
   - On an 18 GB Mac, unload the model between runs (`ollama stop gpt-oss:20b`) to
     avoid swapping.

**Doing a run by hand in the GUI instead.**
1. Run `python3 scripts/stage_run.py N` and load the printed files in QGIS.
2. Start a new plugin chat, paste the prompt exactly, and don't add follow-ups.
3. If it ends in an error, start a new chat with the same prompt, up to 3 attempts.
4. Paste the response and code into the transcript, and fill in the observation
   columns before reading the answer key.

**LLM-Geo** was the planned fallback. It only calls OpenAI, so it wasn't used.

