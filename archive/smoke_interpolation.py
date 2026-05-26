"""
v4: 연기 가림 보간 peak detection.

원리:
1. 강한 threshold로 신뢰도 높은 peak 검출
2. autocorrelation으로 expected period 추정
3. 인접 peak 간격이 period * 1.5 이상이면 누락 의심
4. 누락 위치(start + period*k)에서 ± period*0.3 window 안 max가 weak_threshold 이상이면 보간 peak로 추가
5. weak도 없으면 완전 가림으로 인정 (그대로 둠)

먼저 outlier 5개 row에 적용해서 검증.
"""
import cv2
import numpy as np
import json
import os
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, correlate

VIDEO_DIR = r"G:\FIRIC"
OUT_DIR = r"C:\Users\USER\Firic_regular\samples\outliers"
FPS = 30000 / 1001
CONFIG_PATH = r"C:\Users\USER\Firic_regular\samples\roi_config_final.json"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = json.load(f)

OUTLIERS = [
    ("CHEOEUM", 3, 11697, 11743, 3, 117.27),
    ("CHEOEUM", 20, 12270, 12316, 3, 117.27),
    ("CHEOEUM", 26, 12520, 12582, 4, 116.01),
    ("ONBADA", 14, 6044, 6094, 2, 71.93),
    ("ONBADA", 17, 6170, 6221, 2, 70.52),
]


def red_score(roi):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, (0, 100, 50), (10, 255, 255))
    m2 = cv2.inRange(hsv, (170, 100, 50), (180, 255, 255))
    return float((m1 | m2).sum()) / (roi.shape[0] * roi.shape[1] * 255)


def yellow_score(roi):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (15, 80, 80), (35, 255, 255))
    return float(m.sum()) / (roi.shape[0] * roi.shape[1] * 255)


def estimate_period(signal, min_lag=3, max_lag=150):
    s = signal - signal.mean()
    if s.std() == 0:
        return None
    ac = correlate(s, s, mode="full")
    ac = ac[len(s) - 1:]
    if ac[0] <= 0:
        return None
    ac = ac / ac[0]
    peaks, _ = find_peaks(ac[min_lag:min(max_lag, len(ac))], height=0.15)
    return int(peaks[0] + min_lag) if len(peaks) else None


def smoke_aware_peaks(scores, period, h_strong, h_weak, gap_factor=1.5, window_factor=0.3):
    strong_peaks, _ = find_peaks(scores, height=h_strong, distance=max(3, int(period * 0.6)))
    if len(strong_peaks) < 2:
        return strong_peaks, []
    interpolated = []
    gap_threshold = period * gap_factor
    for i in range(len(strong_peaks) - 1):
        gap = strong_peaks[i + 1] - strong_peaks[i]
        if gap > gap_threshold:
            expected_count = round(gap / period)
            for k in range(1, expected_count):
                expected_pos = strong_peaks[i] + int(period * k)
                w = int(period * window_factor)
                lo = max(0, expected_pos - w)
                hi = min(len(scores), expected_pos + w)
                window = scores[lo:hi]
                if len(window) == 0:
                    continue
                local_max_idx = lo + window.argmax()
                if scores[local_max_idx] >= h_weak:
                    if not any(abs(local_max_idx - p) < int(period * 0.4) for p in list(strong_peaks) + interpolated):
                        interpolated.append(local_max_idx)
    all_peaks = sorted(list(strong_peaks) + interpolated)
    return np.array(all_peaks), interpolated


for sheet, row_n, i0, i1, rot_xl, rpm_xl in OUTLIERS:
    info = cfg[sheet]
    video_path = os.path.join(VIDEO_DIR, info["video"])
    fx, fy, fw, fh = info["fine_roi"]

    pre = 30
    post = 30
    start = i0 - pre
    end = i1 + post

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

    period_r = estimate_period(reds) or 30
    period_y = estimate_period(yels) or 30
    h_r_strong = max(0.015, reds.mean() + 0.5 * reds.std())
    h_r_weak = max(0.005, reds.mean() * 1.2)
    h_y_strong = max(0.015, yels.mean() + 0.5 * yels.std())
    h_y_weak = max(0.005, yels.mean() * 1.2)

    rp_all, rp_interp = smoke_aware_peaks(reds, period_r, h_r_strong, h_r_weak)
    yp_all, yp_interp = smoke_aware_peaks(yels, period_y, h_y_strong, h_y_weak)
    r_pf_all = frames[rp_all]
    y_pf_all = frames[yp_all]
    r_pf_interp = frames[rp_interp] if rp_interp else np.array([])
    y_pf_interp = frames[yp_interp] if yp_interp else np.array([])

    r_in = r_pf_all[(r_pf_all >= i0 - 3) & (r_pf_all <= i1 + 3)]
    y_in = y_pf_all[(y_pf_all >= i0 - 3) & (y_pf_all <= i1 + 3)]
    rot_auto_v4 = len(r_in) - 1 if len(r_in) >= 2 else (len(y_in) - 1 if len(y_in) >= 2 else 0)

    rp_strong, _ = find_peaks(reds, height=h_r_strong, distance=max(3, int(period_r * 0.6)))
    r_strong_in_row = frames[rp_strong][(frames[rp_strong] >= i0 - 3) & (frames[rp_strong] <= i1 + 3)]
    rot_auto_old = len(r_strong_in_row) - 1 if len(r_strong_in_row) >= 2 else 0

    fig, ax = plt.subplots(1, 1, figsize=(16, 6))
    ax.plot(frames, reds, "r-", lw=1.2, alpha=0.7, label="red score")
    ax.plot(frames, yels, "y-", lw=1.2, alpha=0.7, label="yellow score")
    rp_strong_pf = frames[rp_strong]
    ax.plot(rp_strong_pf, reds[rp_strong], "rv", ms=12, label=f"R strong ({len(rp_strong)})")
    if len(rp_interp):
        ax.plot(r_pf_interp, reds[rp_interp], "rx", ms=14, mew=3,
                label=f"R interpolated ({len(rp_interp)})")
    yp_strong, _ = find_peaks(yels, height=h_y_strong, distance=max(3, int(period_y * 0.6)))
    yp_strong_pf = frames[yp_strong]
    ax.plot(yp_strong_pf, yels[yp_strong], "y^", ms=12, label=f"Y strong ({len(yp_strong)})")
    if len(yp_interp):
        ax.plot(y_pf_interp, yels[yp_interp], "yx", ms=14, mew=3,
                label=f"Y interpolated ({len(yp_interp)})")
    ax.axhline(h_r_strong, color="r", ls=":", alpha=0.4, label=f"R strong th={h_r_strong:.3f}")
    ax.axhline(h_r_weak, color="r", ls=":", alpha=0.2, label=f"R weak th={h_r_weak:.3f}")
    ax.axvline(i0, color="g", ls="--", lw=2, label=f"Excel start ({i0})")
    ax.axvline(i1, color="b", ls="--", lw=2, label=f"Excel end ({i1})")
    ax.set_title(f"{sheet} row {row_n} | Excel {rot_xl} rot | "
                 f"Old auto {rot_auto_old} rot → v4 auto {rot_auto_v4} rot "
                 f"(period R={period_r}, Y={period_y})", fontsize=11)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(alpha=0.3)
    ax.set_xlabel("Frame #")
    ax.set_ylabel("Score")

    plt.tight_layout()
    out_png = os.path.join(OUT_DIR, f"{sheet}_row{row_n:02d}_v4.png")
    plt.savefig(out_png, dpi=95, bbox_inches="tight")
    plt.close()
    print(f"{sheet} row {row_n}: Excel {rot_xl}, old auto {rot_auto_old}, v4 auto {rot_auto_v4}")
