# Raw console logs

`<run_id>.log` is everything the plugin printed during an attempt, captured by
`scripts/copilot_driver.py`. That includes the data overview the model was shown,
such as each layer's CRS and column names with sample values. `<run_id>.qgis_console.txt`
is QGIS's own stdout and stderr.

These logs include prompt text and messages printed by the GIS Copilot plugin
(https://github.com/Teakinboyewa/SpatialAnalysisAgent), which is licensed under
GPL-3.0. They are included unchanged, so the records can be checked.
