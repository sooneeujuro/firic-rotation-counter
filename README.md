# firic-rotation-counter

<!-- After Zenodo issues the DOI, replace 1250672477 and 20402770 below.
     The badge URL is shown on your Zenodo deposit page. -->
[![DOI](https://zenodo.org/badge/1250672477.svg)](https://doi.org/10.5281/zenodo.20402770)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Automated rotation counting from underwater ROV flowmeter videos.

Replaces frame-by-frame manual counting of an impeller-driven flowmeter
(red / yellow / reflective markers on a rotating indicator) with a
two-stage ROI pipeline and smoke-aware peak detection. Validated against
~230 manually-measured 30-second segments across 10 dive videos.

## Result summary

| Metric | Value |
|---|---|
| Sheets | 11 (10 unique videos) |
| Rows compared | 232 |
| Rotation integer match | **224 / 232 (96.6 %)** |
| Median \|relative error\| | **0.00 %** |
| Mean \|relative error\| | 2.79 % |
| 95th percentile \|relative error\| | 8.7 % |
| Bias (auto − manual) | −1.65 RPM |

Eight of the eleven sheets achieve 100 % rotation match. The remaining
mismatches are localized to segments where smoke from the hydrothermal
vent fully occludes the marker for a fraction of a rotation — i.e. the
information is not in the video. The smoke-aware interpolation step
recovers partially occluded rotations but deliberately leaves fully
occluded ones unknown rather than guessing.

![per-sheet comparison](output/all_sheets_compare.png)

## Pipeline

```
video + Excel  ─►  (1) coarse ROI    (manual, one box per video)
                   (2) fine ROI      (automatic, flicker-based)
                   (3) batch measure (HSV peaks + smoke-aware recovery)
                   (4) analyze       (per-row diff vs Excel)
```

The two-stage ROI is the trick: with a single tight ROI you can't
choose the right width without already knowing the rotation period —
fast rotations need a wider ROI than slow ones. The coarse box
contains the *whole* rotation plane, the fine box is then placed
automatically at the global maximum of a flicker map
(p · (1 − p), peaked at p = 0.5) — which naturally excludes static
red regions (ROV flags, animals) and selects the camera-near side of
the rotation when both sides are visible.

For algorithm details see [`docs/algorithm.md`](docs/algorithm.md).

## Repository layout

```
firic-rotation-counter/
├── firic/                 # core library (importable package)
│   ├── detection.py       # HSV masks, peak/period, smoke-aware peaks
│   ├── roi.py             # two-stage ROI (auto fine ROI)
│   ├── pipeline.py        # per-sheet batch processing
│   └── viz.py             # plots
├── scripts/               # numbered runners
│   ├── 1_set_coarse_roi.py
│   ├── 2_compute_fine_roi.py
│   ├── 3_run_batch.py
│   └── 4_analyze.py
├── data/                  # see data/README.md — Excel & videos NOT included
├── docs/
│   ├── algorithm.md       # algorithm description
│   └── publishing.md      # how to publish + get a Zenodo DOI
├── output/                # JSON configs, per-sheet CSVs, plots (gitignored)
├── archive/               # earlier prototype scripts (kept for reference)
├── requirements.txt
├── LICENSE
└── README.md
```

## Quick start

```bash
pip install -r requirements.txt
```

Place videos under `G:\FIRIC\` (or edit `VIDEO_DIR` in each script) and
your measurement spreadsheet at `data/For print.xlsx`
(see [`data/README.md`](data/README.md) for the expected format).

```bash
# step 1 — drag a coarse ROI for each video (one-time, interactive)
python scripts/1_set_coarse_roi.py

# step 2 — auto-detect fine ROI inside each coarse ROI
python scripts/2_compute_fine_roi.py

# step 3 — run the auto-measurement and compare to Excel
python scripts/3_run_batch.py

# step 4 — aggregate stats + Bland-Altman plot
python scripts/4_analyze.py

# step 5 — build the archive xlsx (Methodology + Summary + per-segment sheets)
python scripts/5_export_xlsx.py
# add --rich for boxplot + Manual-vs-Auto + Bland-Altman embedded in Summary
python scripts/5_export_xlsx.py --rich
```

**Works with one or many segments.** Steps 3 and 5 auto-discover which
worksheets in `data/For print.xlsx` to process from the ROI config —
just add boxes for whatever segments you have. A sheet whose name ends
with a digit (e.g. `MARU2`) automatically inherits the ROI of its
prefix (`MARU`).

Outputs land in `output/`:

- `coarse_roi.json`, `roi_config.json` — ROI configuration per segment
- `compare_<segment>.csv` — per-row Excel vs auto comparison
- `summary.csv` — per-segment aggregate stats
- `all_sheets_compare.png`, `agreement_analysis.png` — diagnostic plots
- `firic_analysis_archive.xlsx` — archive-ready workbook with
  Methodology, Summary (per-segment mean RPM bar chart), per-segment
  sheets (manual + auto blocks + embedded ScatterChart of RPM vs time)

## Library usage

```python
from firic import auto_fine_roi, run_batch
import json

with open("output/roi_config.json") as f:
    cfg = json.load(f)

summary, results = run_batch(
    "data/For print.xlsx",
    "G:/FIRIC",
    cfg,
    sheets=["MARU", "CHEOEUM"],
    out_dir="output",
)
print(summary)
```

The lower-level building blocks are also exported:

```python
from firic.detection import red_score, estimate_period, smoke_aware_peaks
from firic.roi import auto_fine_roi
```

## Limitations

- **Static red/yellow features inside the coarse ROI** confuse the
  fine-ROI search if they dominate flicker-weighted pixels. The
  flicker formulation (p · (1 − p)) suppresses constants, but extreme
  cases may need manual fine-ROI override.
- **Full marker occlusion** by smoke or panning camera leaves the
  algorithm short of rotations. Partial occlusion is recovered;
  full is reported as unknown.
- **Sub-frame timing**: a 1-rotation row that spans 12 frames at 30 fps
  has ±1 frame ≈ ±10 % RPM uncertainty no matter how perfect the
  detection is. This shows up as the cluster of ±11.5 RPM differences
  on CHEOEUM_2's 1-rotation rows.

## How to cite

If you use this software in research, please cite the archived release:

> Kim, Heejun (2026). *firic-rotation-counter: automated rotation
> counting from ROV underwater flowmeter videos* (Version 0.1.0)
> [Software]. Zenodo. https://doi.org/10.5281/zenodo.20402770

Machine-readable citation metadata is in
[`CITATION.cff`](CITATION.cff); GitHub renders it as a "Cite this
repository" button on the repo page.

## License

MIT — see [LICENSE](LICENSE).
