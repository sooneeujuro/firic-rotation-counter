"""Batch processing: per-sheet auto measurement and Excel comparison.

For each Excel sheet, the pipeline:
  1. reads (init_frame, final_frame, rotation, rpm) rows,
  2. scores the fine-ROI for red/yellow over the full measurement span,
  3. extracts smoke-aware peaks per color,
  4. matches peaks against each Excel row's [init-tol, final+tol] window,
  5. computes auto rotation count, time, RPM and the diff vs Excel.

Row matching uses a primary/secondary color split based on each sheet's
``Indicator`` column (R or Y) — i.e. whichever color the operator
counted manually is preferred for the auto count. If the primary has
< 2 peaks in a row, falls back to combined R+Y, then to a period-based
estimate.
"""
from __future__ import annotations

import os

import cv2
import numpy as np
import pandas as pd

from .detection import (
    red_score, yellow_score,
    estimate_period, smoke_aware_peaks,
)

FPS_DEFAULT = 30000 / 1001  # 29.97 fps


def process_sheet(
    xlsx_path: str,
    sheet: str,
    video_dir: str,
    config: dict,
    fps: float = FPS_DEFAULT,
):
    """Process one Excel sheet end-to-end.

    Returns
    -------
    res : pd.DataFrame
        Per-row comparison: rotation/rpm xl vs auto, error, peak counts.
    trace : dict
        Time-series data for downstream visualization
        (frames, reds, yels, r_pf, y_pf, fine_roi, indicator).
    """
    info = config[sheet]
    fx, fy, fw, fh = info["fine_roi"]
    video_path = os.path.join(video_dir, info["video"])

    raw = pd.read_excel(xlsx_path, sheet_name=sheet, header=None)
    data = raw.iloc[3:, :6].reset_index(drop=True)
    data.columns = ["init_frame", "final_frame", "time_s",
                    "rotation", "rpm", "timestamp"]
    for c in data.columns:
        data[c] = pd.to_numeric(data[c], errors="coerce")
    data = data.dropna(subset=["init_frame", "final_frame"]).reset_index(drop=True)
    data["init_frame"] = data["init_frame"].astype(int)
    data["final_frame"] = data["final_frame"].astype(int)
    indicator = str(raw.iloc[1, 5]).strip().upper()

    start = int(data["init_frame"].min()) - 10
    end = int(data["final_frame"].max()) + 10

    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start)
    frames, reds, yels = [], [], []
    for f in range(start, end + 1):
        ok, img = cap.read()
        if not ok:
            break
        roi_img = img[fy:fy + fh, fx:fx + fw]
        frames.append(f)
        reds.append(red_score(roi_img))
        yels.append(yellow_score(roi_img))
    cap.release()
    frames = np.array(frames)
    reds = np.array(reds)
    yels = np.array(yels)

    h_r_strong = max(0.015, reds.mean() + 0.5 * reds.std())
    h_y_strong = max(0.015, yels.mean() + 0.5 * yels.std())
    h_r_weak = max(0.005, reds.mean() * 1.2)
    h_y_weak = max(0.005, yels.mean() * 1.2)
    period_r = estimate_period(reds) or 30
    period_y = estimate_period(yels) or 30
    rp, rp_interp = smoke_aware_peaks(reds, period_r, h_r_strong, h_r_weak)
    yp, yp_interp = smoke_aware_peaks(yels, period_y, h_y_strong, h_y_weak)
    r_pf = frames[rp]
    y_pf = frames[yp]

    is_y = indicator == "Y"
    primary_pf = y_pf if is_y else r_pf
    secondary_pf = r_pf if is_y else y_pf
    primary_lbl = "Y" if is_y else "R"
    secondary_lbl = "R" if is_y else "Y"
    period_use = (period_y if is_y else period_r) or 30
    tol = max(3, int(period_use * 0.25))

    rows = []
    for i, row in data.iterrows():
        i0, i1 = row["init_frame"], row["final_frame"]
        p_in = primary_pf[(primary_pf >= i0 - tol) & (primary_pf <= i1 + tol)]
        s_in = secondary_pf[(secondary_pf >= i0 - tol) & (secondary_pf <= i1 + tol)]
        combined = np.array(sorted(list(p_in) + list(s_in)))
        if len(p_in) >= 2:
            rot_auto = len(p_in) - 1
            t_auto = (p_in[-1] - p_in[0]) / fps
            rpm_auto = (rot_auto / t_auto) * 60 if t_auto > 0 else np.nan
            src = primary_lbl
        elif len(combined) >= 3:
            rot_auto = (len(combined) - 1) / 2
            t_auto = (combined[-1] - combined[0]) / fps
            rpm_auto = (rot_auto / t_auto) * 60 if t_auto > 0 else np.nan
            src = "R+Y"
        elif len(s_in) >= 2:
            rot_auto = len(s_in) - 1
            t_auto = (s_in[-1] - s_in[0]) / fps
            rpm_auto = (rot_auto / t_auto) * 60 if t_auto > 0 else np.nan
            src = secondary_lbl
        else:
            t_auto = (i1 - i0) / fps
            rot_auto = (i1 - i0) / period_use if period_use else np.nan
            rpm_auto = 60 * fps / period_use if period_use else np.nan
            src = "P-est"
        rows.append({
            "row": i + 1, "init": i0, "final": i1,
            "rot_xl": row["rotation"], "rot_auto": rot_auto,
            "rpm_xl": row["rpm"], "rpm_auto": rpm_auto,
            "src": src, "n_r": int(len(r_pf[(r_pf >= i0 - tol) & (r_pf <= i1 + tol)])),
            "n_y": int(len(y_pf[(y_pf >= i0 - tol) & (y_pf <= i1 + tol)])),
        })
    res = pd.DataFrame(rows)
    res["rpm_err_pct"] = (res["rpm_auto"] - res["rpm_xl"]) / res["rpm_xl"] * 100
    res["rot_match"] = (res["rot_auto"].round() == res["rot_xl"])

    trace = {
        "frames": frames, "reds": reds, "yels": yels,
        "r_pf": r_pf, "y_pf": y_pf,
        "r_interp": frames[rp_interp] if len(rp_interp) else np.array([]),
        "y_interp": frames[yp_interp] if len(yp_interp) else np.array([]),
        "fine_roi": (fx, fy, fw, fh),
        "indicator": indicator,
        "period_r": period_r, "period_y": period_y,
    }
    return res, trace


def run_batch(
    xlsx_path: str,
    video_dir: str,
    config: dict,
    sheets: list[str],
    out_dir: str,
    fps: float = FPS_DEFAULT,
):
    """Run process_sheet over many sheets and write per-sheet CSVs + summary.

    Parameters
    ----------
    out_dir : str
        Output directory. Per-sheet CSVs and summary.csv are written here.

    Returns
    -------
    summary_df : pd.DataFrame
    all_results : dict[sheet, (res, trace)]
    """
    os.makedirs(out_dir, exist_ok=True)
    all_results = {}
    summary = []
    for sheet in sheets:
        if sheet not in config or not config[sheet].get("fine_roi"):
            print(f"SKIP {sheet}: no fine_roi")
            continue
        res, trace = process_sheet(xlsx_path, sheet, video_dir, config, fps=fps)
        all_results[sheet] = (res, trace)
        valid = res.dropna(subset=["rpm_auto"])
        n_match = int(valid["rot_match"].sum())
        summary.append({
            "sheet": sheet,
            "indicator": trace["indicator"],
            "n_rows": len(res),
            "matched": f"{n_match}/{len(valid)}",
            "match_pct": n_match / len(valid) * 100 if len(valid) else 0.0,
            "mean_rpm_err_pct": float(valid["rpm_err_pct"].abs().mean()),
            "mean_rpm_xl": float(valid["rpm_xl"].mean()),
            "mean_rpm_auto": float(valid["rpm_auto"].mean()),
        })
        res.to_csv(os.path.join(out_dir, f"compare_{sheet}.csv"), index=False)
    summary_df = pd.DataFrame(summary)
    summary_df.to_csv(os.path.join(out_dir, "summary.csv"), index=False)
    return summary_df, all_results
