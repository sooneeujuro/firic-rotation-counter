"""Step 4 — aggregate per-sheet CSVs and produce agreement statistics.

Outputs:
  - console: overall + per-sheet stats, outlier rows
  - output/agreement_analysis.png: Bland-Altman + error distribution
"""
from __future__ import annotations

import glob
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from firic.viz import plot_agreement  # noqa: E402

OUT_DIR = os.path.join(ROOT, "output")


def main():
    csv_files = sorted(glob.glob(os.path.join(OUT_DIR, "compare_*.csv")))
    if not csv_files:
        print("No compare_*.csv files. Run scripts/3_run_batch.py first.")
        return
    all_rows = []
    for csv in csv_files:
        sheet = os.path.basename(csv).replace("compare_", "").replace(".csv", "")
        df = pd.read_csv(csv)
        df["sheet"] = sheet
        all_rows.append(df)
    df = pd.concat(all_rows, ignore_index=True)
    df = df.dropna(subset=["rpm_auto", "rpm_xl"]).reset_index(drop=True)
    df["rpm_diff"] = df["rpm_auto"] - df["rpm_xl"]
    df["rpm_err_abs"] = df["rpm_diff"].abs()
    df["rot_match"] = (df["rot_auto"].round() == df["rot_xl"])

    print("=" * 80)
    print(f"Overall (n={len(df)})")
    print("=" * 80)
    print(f"  Rotation integer match : {df['rot_match'].sum()}/{len(df)} "
          f"({df['rot_match'].mean() * 100:.1f}%)")
    print(f"  RPM mean |abs err|     : {df['rpm_err_abs'].mean():.2f} RPM")
    print(f"  RPM median |abs err|   : {df['rpm_err_abs'].median():.2f} RPM")
    print(f"  RPM 95%ile |abs err|   : {df['rpm_err_abs'].quantile(0.95):.2f} RPM")
    print(f"  RPM mean |rel err|     : {df['rpm_err_pct'].abs().mean():.2f} %")
    print(f"  RPM median |rel err|   : {df['rpm_err_pct'].abs().median():.2f} %")
    print(f"  Bias (mean diff)       : {df['rpm_diff'].mean():+.2f} RPM")

    print("\nPer sheet:")
    by_sheet = df.groupby("sheet").agg(
        n=("row", "count"),
        rot_match=("rot_match", lambda x: f"{x.sum()}/{len(x)} ({x.mean() * 100:.0f}%)"),
        mean_abs=("rpm_err_abs", "mean"),
        median_abs=("rpm_err_abs", "median"),
        max_abs=("rpm_err_abs", "max"),
        mean_pct=("rpm_err_pct", lambda x: x.abs().mean()),
        bias=("rpm_diff", "mean"),
    ).round(2)
    print(by_sheet.to_string())

    out_png = os.path.join(OUT_DIR, "agreement_analysis.png")
    plot_agreement(df, out_png)
    print(f"\nsaved {out_png}")


if __name__ == "__main__":
    main()
