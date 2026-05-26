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


def main():
    import re
    import pandas as pd

    with open(ROI_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    available_sheets = pd.ExcelFile(XLSX).sheet_names

    def _sheet_init_frame(sn: str) -> int | None:
        df = pd.read_excel(XLSX, sheet_name=sn, header=None)
        v = pd.to_numeric(df.iloc[3, 0], errors="coerce")
        return int(v) if pd.notna(v) else None

    # Inherit ROI for sheets like "MARU2" -> "MARU", but read init_frame from the
    # sheet itself so each segment starts at its own measurement window.
    for s in available_sheets:
        if s in cfg:
            init = _sheet_init_frame(s)
            if init is not None:
                cfg[s]["init_frame"] = init
            continue
        m = re.match(r"^(.+?)(\d+)$", s)
        if m and m.group(1) in cfg:
            init = _sheet_init_frame(s)
            cfg[s] = {**cfg[m.group(1)]}
            if init is not None:
                cfg[s]["init_frame"] = init
    sheets = [s for s in available_sheets if s in cfg]

    summary_df, all_results = run_batch(XLSX, VIDEO_DIR, cfg, sheets, OUT_DIR)
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
