# Runs

- `run_log.csv`: one row per run, in the randomized order of the protocol. It records
  status, attempts, final answer, the observation columns, the first-attempt score
  (`score_0_3`) and the pre-registered score (`score_rule_b`, `scored_attempt_rule_b`).
- `transcripts/<run_id>.json`: the full record of one attempt. It holds the agent's
  plan, selected tools, final code, printed output, every code error and the blocked
  network call. `<run_id>.md` is the same record in readable form. `_t2` and `_t3` are
  retries.
- `raw_logs/`: the console output of each attempt (see the README there).
- `batch_20261106_1910.log` and `retry_20261106_2239.log`: start and end times.

Run IDs read `<task>-<data set>-r<replicate>`, for example `C-set1-r1`. Which set is
the trap is in `../answer_keys/ANSWER_KEY.md`.
