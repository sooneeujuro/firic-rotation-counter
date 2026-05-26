"""
Batch main: 12개 시트 전체 자동 측정 vs Excel 수동 측정 비교.
MARU2는 MARU와 동일 영상/ROI 사용.
"""
import cv2
import numpy as np
import json
import os
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, correlate


def estimate_period(signal, min_lag=3, max_lag=200):
    s = signal - signal.mean()
    if s.std() == 0:
        return None
    ac = correlate(s, s, mode="full")
    ac = ac[len(s) - 1:]
    if ac[0] <= 0:
        return None
    ac = ac / ac[0]
    peaks, _ = find_peaks(ac[min_lag:min(max_lag, len(ac))], height=0.15)
    if len(peaks) == 0:
        return None
    return int(peaks[0] + min_lag)


def smoke_aware_peaks(scores, period, h_strong, h_weak,
                      gap_factor=1.5, window_factor=0.3):
    """강한 peak 검출 후, 인접 간격이 period*gap_factor 이상이면
    expected position 부근에서 weak threshold로 보간 peak 탐색."""
    strong, _ = find_peaks(scores, height=h_strong, distance=max(3, int(period * 0.6)))
    if len(strong) < 2:
        return strong, np.array([], dtype=int)
    interp = []
    gap_th = period * gap_factor
    for i in range(len(strong) - 1):
        gap = strong[i + 1] - strong[i]
        if gap > gap_th:
            n_missing = round(gap / period) - 1
            for k in range(1, n_missing + 1):
                exp_pos = strong[i] + int(period * k)
                w = int(period * window_factor)
                lo = max(0, exp_pos - w)
                hi = min(len(scores), exp_pos + w)
                window = scores[lo:hi]
                if len(window) == 0:
                    continue
                local_max_idx = lo + int(window.argmax())
                if scores[local_max_idx] >= h_weak:
                    # 기존 peak와 너무 가까우면 skip
                    too_close = any(abs(local_max_idx - p) < int(period * 0.4)
                                    for p in list(strong) + interp)
                    if not too_close:
                        interp.append(local_max_idx)
    all_pk = np.array(sorted(list(strong) + interp))
    return all_pk, np.array(interp, dtype=int)

XLSX = r"C:\Users\USER\Firic_regular\For print.xlsx"
VIDEO_DIR = r"G:\FIRIC"
OUT_DIR = r"C:\Users\USER\Firic_regular\samples"
FPS = 30000 / 1001
MERGE_GAP = 4

with open(os.path.join(OUT_DIR, "roi_config_final.json"), "r", encoding="utf-8") as f:
    cfg = json.load(f)

cfg["MARU2"] = {**cfg["MARU"]}

SHEETS = ["MARU", "MARU2", "CHEOEUM", "CHEOEUM_2", "ONNURI",
          "SAERO_1", "SAERO_2", "ONBADA", "ONBADA_2", "ONNARE", "ONNARE_2"]


def red_score(roi):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, (0, 100, 50), (10, 255, 255))
    m2 = cv2.inRange(hsv, (170, 100, 50), (180, 255, 255))
    return float((m1 | m2).sum()) / (roi.shape[0] * roi.shape[1] * 255)


def yellow_score(roi):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (15, 80, 80), (35, 255, 255))
    return float(m.sum()) / (roi.shape[0] * roi.shape[1] * 255)


def process_sheet(sheet):
    info = cfg[sheet]
    fx, fy, fw, fh = info["fine_roi"]
    video_path = os.path.join(VIDEO_DIR, info["video"])

    raw = pd.read_excel(XLSX, sheet_name=sheet, header=None)
    data = raw.iloc[3:, :6].reset_index(drop=True)
    data.columns = ["init_frame", "final_frame", "time_s", "rotation", "rpm", "timestamp"]
    for c in data.columns:
        data[c] = pd.to_numeric(data[c], errors="coerce")
    data = data.dropna(subset=["init_frame", "final_frame"]).reset_index(drop=True)
    data["init_frame"] = data["init_frame"].astype(int)
    data["final_frame"] = data["final_frame"].astype(int)
    indicator = str(raw.iloc[1, 5]).strip()

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

    rows = []
    is_y = indicator.upper() == "Y"
    primary_pf = y_pf if is_y else r_pf
    secondary_pf = r_pf if is_y else y_pf
    primary_lbl = "Y" if is_y else "R"
    secondary_lbl = "R" if is_y else "Y"
    period_primary = period_y if is_y else period_r
    period_use = period_primary if period_primary else (period_r or period_y or 30)
    tol = max(3, int(period_use * 0.25))
    for i, row in data.iterrows():
        i0, i1 = row["init_frame"], row["final_frame"]
        p_in = primary_pf[(primary_pf >= i0 - tol) & (primary_pf <= i1 + tol)]
        s_in = secondary_pf[(secondary_pf >= i0 - tol) & (secondary_pf <= i1 + tol)]
        combined = np.array(sorted(list(p_in) + list(s_in)))
        if len(p_in) >= 2:
            rot_auto = len(p_in) - 1
            t_auto = (p_in[-1] - p_in[0]) / FPS
            rpm_auto = (rot_auto / t_auto) * 60 if t_auto > 0 else np.nan
            src = primary_lbl
        elif len(combined) >= 3:
            rot_auto = (len(combined) - 1) / 2
            t_auto = (combined[-1] - combined[0]) / FPS
            rpm_auto = (rot_auto / t_auto) * 60 if t_auto > 0 else np.nan
            src = "R+Y"
        elif len(s_in) >= 2:
            rot_auto = len(s_in) - 1
            t_auto = (s_in[-1] - s_in[0]) / FPS
            rpm_auto = (rot_auto / t_auto) * 60 if t_auto > 0 else np.nan
            src = secondary_lbl
        else:
            t_auto = (i1 - i0) / FPS
            rot_auto = (i1 - i0) / period_use if period_use else np.nan
            rpm_auto = 60 * FPS / period_use if period_use else np.nan
            src = "P-est"
        r_in = r_pf[(r_pf >= i0 - tol) & (r_pf <= i1 + tol)]
        y_in = y_pf[(y_pf >= i0 - tol) & (y_pf <= i1 + tol)]
        rows.append({
            "row": i + 1, "init": i0, "final": i1,
            "rot_xl": row["rotation"], "rot_auto": rot_auto,
            "rpm_xl": row["rpm"], "rpm_auto": rpm_auto,
            "src": src, "n_r": len(r_in), "n_y": len(y_in),
        })
    res = pd.DataFrame(rows)
    res["rpm_err_%"] = (res["rpm_auto"] - res["rpm_xl"]) / res["rpm_xl"] * 100
    return res, frames, reds, yels, r_pf, y_pf, indicator


all_results = {}
summary = []
fig, axes = plt.subplots(6, 2, figsize=(20, 24))
axes = axes.flatten()

for i, sheet in enumerate(SHEETS):
    if sheet not in cfg or not cfg[sheet].get("fine_roi"):
        print(f"SKIP {sheet}: no fine_roi")
        continue
    res, frames, reds, yels, r_pf, y_pf, indicator = process_sheet(sheet)
    all_results[sheet] = res

    valid = res.dropna(subset=["rpm_auto"])
    n_match = (valid["rot_auto"] == valid["rot_xl"]).sum()
    mean_err = valid["rpm_err_%"].abs().mean()
    summary.append({
        "sheet": sheet, "indicator": indicator, "n_rows": len(res),
        "matched": f"{n_match}/{len(valid)}",
        "match_%": n_match / len(valid) * 100 if len(valid) else 0,
        "mean_rpm_err_%": mean_err,
        "mean_rpm_xl": valid["rpm_xl"].mean(),
        "mean_rpm_auto": valid["rpm_auto"].mean(),
    })

    ax = axes[i]
    ax.plot(res["row"], res["rpm_xl"], "go-", label="Excel", ms=6)
    ax.plot(res["row"], res["rpm_auto"], "r^-", label="Auto", ms=5)
    ax.set_title(f"{sheet} ({indicator}) | match={n_match}/{len(valid)} | err={mean_err:.1f}%", fontsize=10)
    ax.set_xlabel("row")
    ax.set_ylabel("RPM")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    res.to_csv(os.path.join(OUT_DIR, f"compare_{sheet}.csv"), index=False)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "all_sheets_compare.png"), dpi=85, bbox_inches="tight")

summary_df = pd.DataFrame(summary)
summary_df.to_csv(os.path.join(OUT_DIR, "summary.csv"), index=False)
print()
print(summary_df.to_string(index=False,
                           formatters={"match_%": "{:.0f}".format,
                                       "mean_rpm_err_%": "{:.2f}".format,
                                       "mean_rpm_xl": "{:.1f}".format,
                                       "mean_rpm_auto": "{:.1f}".format}))
print(f"\nTotal matched: {sum(int(s['matched'].split('/')[0]) for s in summary)}/{sum(int(s['matched'].split('/')[1]) for s in summary)}")
print(f"Mean RPM error: {summary_df['mean_rpm_err_%'].mean():.2f}%")
print(f"\nsaved all_sheets_compare.png + per-sheet CSVs + summary.csv")
