"""Step 5 — export an archive-ready Excel workbook.

Combines the per-sheet auto-measurement results with the original manual
spreadsheet into a single xlsx with:
  - Methodology sheet (algorithm summary, DOI, author, citation)
  - Summary sheet (per-sheet accuracy table)
  - One worksheet per vent (manual + auto columns, outlier highlighting)

Output: ``output/firic_analysis_archive.xlsx``
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from firic import run_batch  # noqa: E402
from firic.export import export_archive_xlsx  # noqa: E402

XLSX_IN = os.path.join(ROOT, "data", "For print.xlsx")
VIDEO_DIR = r"G:\FIRIC"
ROI_PATH = os.path.join(ROOT, "output", "roi_config.json")
OUT_DIR = os.path.join(ROOT, "output")
OUT_PATH = os.path.join(OUT_DIR, "firic_analysis_archive.xlsx")

DOI = "10.5281/zenodo.20402770"
AUTHOR = "Kim, Heejun"
AFFILIATION = "Korea Institute of Ocean Science & Technology"

SHEETS = ["MARU", "MARU2", "CHEOEUM", "CHEOEUM_2", "ONNURI",
          "SAERO_1", "SAERO_2", "ONBADA", "ONBADA_2", "ONNARE", "ONNARE_2"]


def main():
    with open(ROI_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    if "MARU" in cfg and "MARU2" not in cfg:
        cfg["MARU2"] = {**cfg["MARU"]}

    summary_df, all_results = run_batch(XLSX_IN, VIDEO_DIR, cfg, SHEETS, OUT_DIR)

    out = export_archive_xlsx(
        src_xlsx_path=XLSX_IN,
        summary_df=summary_df,
        all_results=all_results,
        out_path=OUT_PATH,
        doi=DOI,
        author=AUTHOR,
        affiliation=AFFILIATION,
    )
    print(f"saved {out}")


if __name__ == "__main__":
    main()
