"""Run one GIS Copilot 1.4 request inside a real QGIS session, without clicking.

Launched by run_local.sh as:  qgis --code copilot_driver.py
Settings come from environment variables (see run_local.sh).

What it reproduces from the plugin's dock widget (SpatialAnalysisAgent_dockwidget.py):
  - layers are added to the project; data_path = visible layers' source paths,
    one per line (dockwidget lines ~725-744)
  - [LocalModel] base_url/model/api_key are written to the plugin's config.ini and
    the model name is registered with the Ollama provider (save_local_model_settings)
  - SpatialAnalysisAgent_MyScript.py is exec'd with the same local variables, and
    with __file__ pointing at the dock widget module, as ScriptThread does
  - is_review = False (the checkbox default in the .ui file); reasoning effort 'medium'

Deliberate differences (each is written into the transcript):
  1. Network guard: any connection that is not to localhost is refused and logged.
     This blocks the unconditional POST to gibd.online/api/feedback at the end of
     MyScript (it is sent even with a local model) without changing what the model
     sees or does.
  2. matplotlib uses the Agg backend, so plt.show() cannot open a window and hang.
  3. Each run has its own workspace folder.
"""
import builtins
import csv
import datetime as dt
import io
import json
import os
import socket
import sys
import threading
import time
import traceback
from pathlib import Path

from qgis.PyQt.QtCore import QTimer
from qgis.core import QgsProject, QgsVectorLayer
from qgis.utils import iface

ENV = os.environ
KIT = Path(ENV["TRAP_KIT"])
PLUGIN = Path(ENV["TRAP_PLUGIN_DIR"])          # .../plugins/SpatialAnalysisAgent-master
MODEL = ENV.get("TRAP_MODEL", "gpt-oss:20b")
BASE_URL = ENV.get("TRAP_BASE_URL", "http://127.0.0.1:11434/v1")
RUN_DIR = Path(ENV["TRAP_RUN_DIR"])            # ~/gis_work/runNN (already staged)
RUN_ID = ENV["TRAP_RUN_ID"]                    # e.g. B-set1-r1, or smoke
TASK_FILE = Path(ENV["TRAP_TASK_FILE"])
OUT_DIR = Path(ENV.get("TRAP_OUT_DIR", str(KIT / "runs" / "transcripts")))
TIMEOUT_MIN = float(ENV.get("TRAP_TIMEOUT_MIN", "75"))

OUT_DIR.mkdir(parents=True, exist_ok=True)
RAW_LOG = OUT_DIR / f"{RUN_ID}.log"
MD = OUT_DIR / f"{RUN_ID}.md"
JSN = OUT_DIR / f"{RUN_ID}.json"

blocked = []
started = time.time()
state = {"done": False}


# ---------------------------------------------------------------- network guard
_LOCAL = {"127.0.0.1", "::1", "localhost"}
_orig_getaddrinfo = socket.getaddrinfo
_orig_connect = socket.socket.connect


def _guard_getaddrinfo(host, *a, **k):
    if host not in _LOCAL and host is not None:
        blocked.append({"t": round(time.time() - started, 1), "kind": "dns", "host": str(host)})
        raise OSError(f"[trap-driver] blocked non-local lookup: {host}")
    return _orig_getaddrinfo(host, *a, **k)


def _guard_connect(self, address):
    host = address[0] if isinstance(address, tuple) else address
    if host not in _LOCAL:
        blocked.append({"t": round(time.time() - started, 1), "kind": "connect", "host": str(host)})
        raise OSError(f"[trap-driver] blocked non-local connection: {host}")
    return _orig_connect(self, address)


socket.getaddrinfo = _guard_getaddrinfo
socket.socket.connect = _guard_connect

import requests  # noqa: E402

_orig_post = requests.post


class _FakeResponse:
    status_code = 204
    text = ""
    ok = True

    def json(self):
        return {}


def _guard_post(url, *a, **k):
    if "127.0.0.1" in url or "localhost" in url:
        return _orig_post(url, *a, **k)
    payload = k.get("json") or {}
    blocked.append({"t": round(time.time() - started, 1), "kind": "requests.post", "url": url,
                    "payload_keys": sorted(payload.keys()) if isinstance(payload, dict) else str(type(payload))})
    return _FakeResponse()


requests.post = _guard_post

import matplotlib  # noqa: E402

matplotlib.use("Agg", force=True)


# ---------------------------------------------------------------- output capture
class Tee(io.TextIOBase):
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            try:
                st.write(s)
                st.flush()
            except Exception:
                pass
        return len(s)

    def flush(self):
        for st in self.streams:
            try:
                st.flush()
            except Exception:
                pass


raw = open(RAW_LOG, "w", encoding="utf-8")


def write_outputs(result, status):
    elapsed = round((time.time() - started) / 60, 1)
    g = lambda k: result.get(k) if isinstance(result, dict) else None  # noqa: E731
    record = {
        "run_id": RUN_ID, "status": status, "elapsed_min": elapsed,
        "finished_et": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "agent": "GIS Copilot (AutonomousGIS-SpatialAnalysisAgent) 1.4, official plugin zip",
        "model": MODEL, "provider": f"local (Ollama) {BASE_URL}",
        "task": TASK_FILE.read_text().strip(), "data_path": g("data_path"),
        "task_name": g("task_name"), "task_breakdown": g("task_breakdown"),
        "selected_tools": g("selected_tools"), "final_code": g("generated_code"),
        "program_output": g("output"), "error_collector": g("error_collector"),
        "exec_exception": g("exec_exception"), "blocked_network": blocked,
        "workspace_files": sorted(p.name for p in (RUN_DIR / "workspace").glob("*")) if (RUN_DIR / "workspace").exists() else [],
    }
    JSN.write_text(json.dumps(record, indent=2, default=str))
    errs = record["error_collector"] or []
    lines = [
        f"# Run {RUN_ID}", "",
        f"- Finished (ET): {record['finished_et']}  ·  elapsed {elapsed} min  ·  status: **{status}**",
        f"- Agent: {record['agent']}",
        f"- Model: {MODEL} via {record['provider']}",
        f"- Code-execution attempts that failed: {len(errs)} (plugin's own debugger, up to 5)",
        "- Driver differences from clicking Run: non-local network blocked; matplotlib Agg; per-run workspace.",
        f"- Blocked network calls: {len(blocked)} "
        + (f"({', '.join(sorted({b.get('url') or b.get('host') for b in blocked}))})" if blocked else ""),
        "", "## Prompt (verbatim)", "", record["task"], "",
        "## Task breakdown (the agent's own plan)", "", str(record["task_breakdown"] or "(none)"), "",
        "## Selected tools", "", str(record["selected_tools"] or "(none)"), "",
        "## Program output (what the agent reported)", "", "```", str(record["program_output"] or "(none)"), "```", "",
        "## Final code", "", "```python", str(record["final_code"] or "(none)"), "```", "",
    ]
    if errs:
        lines += ["## Execution errors along the way", ""]
        for e in errs:
            lines += [f"- Attempt {e.get('attempt')}: `{str(e.get('error_message'))[:300]}`"]
        lines.append("")
    if record["exec_exception"]:
        lines += ["## Exception in the plugin script", "", "```", record["exec_exception"], "```", ""]
    lines += ["## Workspace files", "", ", ".join(record["workspace_files"]) or "(none)", "",
              f"Full console log: `{RAW_LOG.name}`", "",
              "## What I observed (fill in before opening the answer key)", "",
              "- Generic caveat? (quote)", "- Named the specific problem? (quote)",
              "- Fixed it? How?", "- Task A only: which tool or function computed area?", ""]
    MD.write_text("\n".join(lines))


def finish(result, status, code):
    if state["done"]:
        return
    state["done"] = True
    try:
        sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__
        write_outputs(result, status)
        raw.flush()
        raw.close()
    finally:
        os._exit(code)


def watchdog():
    finish({"exec_exception": f"Timed out after {TIMEOUT_MIN} min"}, "timeout", 4)


# ---------------------------------------------------------------- the run
def run():
    result = {}
    try:
        tee = Tee(raw, sys.__stdout__)
        sys.stdout = sys.stderr = tee

        # 1. Layers into the project, as a user would add them.
        QgsProject.instance().clear()
        for p in sorted(RUN_DIR.glob("*.gpkg")):
            lyr = QgsVectorLayer(str(p), p.stem, "ogr")
            if not lyr.isValid():
                raise RuntimeError(f"Layer failed to load: {p}")
            QgsProject.instance().addMapLayer(lyr)
        root = QgsProject.instance().layerTreeRoot()
        data_path = "\n".join(n.layer().dataProvider().dataSourceUri().split("|")[0]
                              for n in root.findLayers() if n.layer() and n.isVisible())
        workspace = RUN_DIR / "workspace"
        workspace.mkdir(exist_ok=True)

        # 2. Local-model settings, as the plugin's settings tab saves them.
        inner = PLUGIN / "SpatialAnalysisAgent"
        import configparser
        cfg_path = inner / "config.ini"
        cfg = configparser.ConfigParser()
        if cfg_path.exists():
            cfg.read(cfg_path)
        if "API_Key" not in cfg:
            # What the dock widget's update_config_file() writes on first open when the
            # key field is empty (a local-model user has no OpenAI key).
            cfg["API_Key"] = {"OpenAI_key": ""}
        cfg["LocalModel"] = {"base_url": BASE_URL, "model": MODEL, "api_key": "no-api"}
        with open(cfg_path, "w") as f:
            cfg.write(f)
        if str(inner) not in sys.path:
            sys.path.insert(0, str(inner))
        from SpatialAnalysisAgent_ModelProvider import ModelProviderFactory
        ModelProviderFactory.register_model(MODEL, "ollama")

        task = TASK_FILE.read_text().strip()
        print(f"[trap-driver] run {RUN_ID}  model {MODEL}  data_path:\n{data_path}\n", flush=True)

        # 3. Execute the plugin's own script exactly as ScriptThread does.
        script_path = inner / "SpatialAnalysisAgent_MyScript.py"
        exec_globals = {"__name__": "SpatialAnalysisAgent_dockwidget_exec",
                        "__file__": str(PLUGIN / "SpatialAnalysisAgent_dockwidget.py"),
                        "__builtins__": builtins}

        class _Sig:
            def emit(self, *a, **k):
                pass

        local_vars = {
            "task": task, "data_path": data_path, "workspace_directory": str(workspace),
            "model_name": MODEL, "is_review": False, "reasoning_effort_value": "medium",
            "check_running": lambda: True, "_is_running": True,
            "output_signal": _Sig(), "streaming_callback": lambda *a, **k: None,
            "print": lambda *a, **k: builtins.print(*a, **k, flush=True),
        }
        try:
            exec(compile(script_path.read_text(), str(script_path), "exec"), exec_globals, local_vars)
            status = "completed"
        except BaseException:
            local_vars["exec_exception"] = traceback.format_exc()
            print(local_vars["exec_exception"], flush=True)
            status = "script-exception"
        result = {k: local_vars.get(k) for k in ("task_name", "task_breakdown", "selected_tools",
                                                 "generated_code", "output", "error_collector",
                                                 "exec_exception")}
        result["data_path"] = data_path
        errs = result.get("error_collector") or []
        if status == "completed" and len(errs) >= 5:
            status = "code-failed-5-times"
        try:
            iface.mapCanvas().refreshAllLayers()
            iface.mapCanvas().saveAsImage(str(OUT_DIR / f"{RUN_ID}_map.png"))
        except Exception:
            pass
        finish(result, status, 0)
    except BaseException:
        result["exec_exception"] = traceback.format_exc()
        finish(result, "driver-error", 3)


threading.Timer(TIMEOUT_MIN * 60, watchdog).start()
QTimer.singleShot(4000, run)
