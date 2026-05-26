"""Step 3 — run the auto-measurement on every sheet and compare to Excel.

Reads ``output/roi_config.json``, processes every sheet (including
MARU2, which shares MARU's ROI), writes per-sheet ``compare_*.csv``
and ``summary.csv`` to ``output/``, plus an overview grid plot.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from firic import run_batch  # noqa: E402
from firic.viz import plot_summary_grid  # noqa: E402

XLSX = os.path.join(ROOT, "data", "For print.xlsx")
VIDEO_DIR = r"G:\FIRIC"
ROI_PATH = os.path.join(ROOT, "output", "roi_config.json")
OUT_DIR = os.path.join(ROOT, "output")

SHEETS = ["MARU", "MARU2", "CHEOEUM", "CHEOEUM_2", "ONNURI",
          "SAERO_1", "SAERO_2", "ONBADA", "ONBADA_2", "ONNARE", "ONNARE_2"]


def main():
    with open(ROI_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    if "MARU" in cfg and "MARU2" not in cfg:
        cfg["MARU2"] = {**cfg["MARU"]}

    summary_df, all_results = run_batch(XLSX, VIDEO_DIR, cfg, SHEETS, OUT_DIR)
    print(summary_df.to_string(
        index=False,
        formatters={
            "match_pct": "{:.0f}".format,
            "mean_rpm_err_pct": "{:.2f}".format,
            "mean_rpm_xl": "{:.1f}".format,
            "mean_rpm_auto": "{:.1f}".format,
        },
    ))
    n_match = sum(int(s["matched"].split("/")[0]) for _, s in summary_df.iterrows())
    n_valid = sum(int(s["matched"].split("/")[1]) for _, s in summary_df.iterrows())
    print(f"\nTotal matched: {n_match}/{n_valid} ({n_match/n_valid*100:.1f}%)")
    print(f"Mean RPM error: {summary_df['mean_rpm_err_pct'].mean():.2f}%")

    plot_summary_grid(all_results, os.path.join(OUT_DIR, "all_sheets_compare.png"))
    print(f"saved {OUT_DIR}/all_sheets_compare.png")


if __name__ == "__main__":
    main()
