# data/

Place your measurement spreadsheet here as `For print.xlsx` (or update
the path in `scripts/3_run_batch.py`). The spreadsheet is **not**
included in this repository — it contains internal measurement data.

## Expected format

One worksheet per video segment. Sheet name = vent ID (e.g. `MARU`,
`CHEOEUM_2`).

| Row | Column A | Column B | Column C | Column D | Column E | Column F |
|---|---|---|---|---|---|---|
| 1 | `Dive #` | `Vent ID` | `Video #` | — | — | `Indicator` |
| 2 | dive code (e.g. `R2370`) | vent name | video filename stem | — | — | `R` or `Y` |
| 3 | `Initial frame #` | `Final frame #` | `Time (s)` | `Rotation` | `RPM` | `Timestamp` |
| 4+ | (per-row measurements) | | | | | |

- **Video filename stem**: matches a file at `G:\FIRIC\<stem>.mov`
  (configurable via `VIDEO_DIR`).
- **Indicator**: `R` if the operator counted using the red marker,
  `Y` if yellow. The pipeline uses this to pick the primary peak channel.
- **Initial / Final frame**: row's measurement endpoints. The same
  marker is expected to return to the reference position at both.
- **Rotation**: integer count of rotations in this row.

See the project README for a description of the algorithm.
