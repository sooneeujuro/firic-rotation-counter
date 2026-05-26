"""
Fine ROI v3: heatmap blur + global max 방식.
가장 깜빡임이 강한 1점 중심으로 좁은 ROI → 양쪽 cluster 중 강한 쪽만 자동 선택.
"""
import cv2
import numpy as np
import json
import os
import pandas as pd
from scipy.signal import find_peaks, correlate
import matplotlib.pyplot as plt

XLSX = r"C:\Users\USER\Firic_regular\For print.xlsx"
VIDEO_DIR = r"G:\FIRIC"
OUT_DIR = r"C:\Users\USER\Firic_regular\samples"
N_FRAMES = 240
FPS = 30000 / 1001
FINE_W = 90
FINE_H = 70

with open(os.path.join(OUT_DIR, "coarse_roi.json"), "r", encoding="utf-8") as f:
    cfg = json.load(f)


def red_mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, (0, 100, 50), (10, 255, 255)) | cv2.inRange(hsv, (170, 100, 50), (180, 255, 255))


def yellow_mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, (15, 80, 80), (35, 255, 255))


def red_score(roi):
    m = red_mask(roi)
    return float(m.sum()) / (roi.shape[0] * roi.shape[1] * 255)


def yellow_score(roi):
    m = yellow_mask(roi)
    return float(m.sum()) / (roi.shape[0] * roi.shape[1] * 255)


def auto_fine_v3(video_path, init_frame, coarse):
    cx, cy, cw, ch = coarse
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, init_frame)
    accum = np.zeros((ch, cw), dtype=np.float32)
    sample = None
    n = 0
    for _ in range(N_FRAMES):
        ok, img = cap.read()
        if not ok:
            break
        if sample is None:
            sample = img.copy()
        roi_img = img[cy:cy + ch, cx:cx + cw]
        accum += (red_mask(roi_img) > 0).astype(np.float32)
        accum += 0.7 * (yellow_mask(roi_img) > 0).astype(np.float32)
        n += 1
    cap.release()
    if n < 10:
        return None, sample, None
    sat_ratio = accum / n
    flicker_weight = sat_ratio * (1.0 - sat_ratio) * 4.0
    flicker_weight = np.clip(flicker_weight, 0, 1)
    blurred = cv2.GaussianBlur(flicker_weight, (15, 15), 0)
    py, px = np.unravel_index(np.argmax(blurred), blurred.shape)
    fw = min(FINE_W, cw)
    fh = min(FINE_H, ch)
    fx_local = max(0, min(cw - fw, int(px - fw // 2)))
    fy_local = max(0, min(ch - fh, int(py - fh // 2)))
    rx = cx + fx_local
    ry = cy + fy_local
    return (int(rx), int(ry), int(fw), int(fh)), sample, blurred


def estimate_period_autocorr(signal, min_lag=3, max_lag=120):
    s = signal - signal.mean()
    ac = correlate(s, s, mode="full")
    ac = ac[len(s) - 1:]
    if ac[0] <= 0:
        return None
    ac = ac / ac[0]
    peaks, _ = find_peaks(ac[min_lag:max_lag], height=0.2)
    if len(peaks) == 0:
        return None
    return int(peaks[0] + min_lag)


results = {}
fig, axes = plt.subplots(10, 3, figsize=(20, 30))

print(f"{'Sheet':<11} {'fine_size':<12} {'period_ac':>10} {'R_pk':>5} {'R_med':>7} {'RPM_auto':>9} {'RPM_xl':>8} {'ratio':>7}")
print("-" * 80)

for idx, (sheet, info) in enumerate(cfg.items()):
    video_path = os.path.join(VIDEO_DIR, info["video"])
    init_f = info["init_frame"]
    coarse = info["coarse_roi"]

    fine, sample, heatmap = auto_fine_v3(video_path, init_f, coarse)
    rgb = cv2.cvtColor(sample, cv2.COLOR_BGR2RGB)
    cx, cy, cw, ch = coarse
    pad_show = 30
    zx0, zy0 = max(0, cx - pad_show), max(0, cy - pad_show)
    zx1, zy1 = min(1920, cx + cw + pad_show), min(1080, cy + ch + pad_show)
    axes[idx, 0].imshow(rgb[zy0:zy1, zx0:zx1], extent=(zx0, zx1, zy1, zy0))
    axes[idx, 0].add_patch(plt.Rectangle((cx, cy), cw, ch, fill=False, ec="orange", lw=2))
    if fine:
        fx, fy, fw, fh = fine
        axes[idx, 0].add_patch(plt.Rectangle((fx, fy), fw, fh, fill=False, ec="lime", lw=3))
    axes[idx, 0].set_title(f"{sheet} | fine={fine}", fontsize=9)
    axes[idx, 0].tick_params(labelsize=7)

    if heatmap is not None:
        axes[idx, 1].imshow(heatmap, cmap="hot", extent=(cx, cx + cw, cy + ch, cy))
        axes[idx, 1].set_title(f"{sheet} flicker weight (blur)", fontsize=9)
        axes[idx, 1].tick_params(labelsize=7)

    raw = pd.read_excel(XLSX, sheet_name=sheet, header=None)
    xl_rpm = float(pd.to_numeric(raw.iloc[3, 4], errors="coerce"))

    if fine:
        fx, fy, fw, fh = fine
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, init_f)
        reds, yels, frames = [], [], []
        for i in range(N_FRAMES):
            ok, img = cap.read()
            if not ok:
                break
            roi_img = img[fy:fy + fh, fx:fx + fw]
            frames.append(init_f + i)
            reds.append(red_score(roi_img))
            yels.append(yellow_score(roi_img))
        cap.release()
        frames = np.array(frames)
        reds = np.array(reds)
        yels = np.array(yels)
        period_ac = estimate_period_autocorr(reds)
        dist = max(3, int(period_ac * 0.6)) if period_ac else 3
        height = max(0.015, reds.mean() + 0.5 * reds.std())
        rp, _ = find_peaks(reds, height=height, distance=dist)
        med = float(np.median(np.diff(rp))) if len(rp) >= 2 else float("nan")
        rpm_auto = 60 * FPS / med if med > 0 else float("nan")
        ratio = rpm_auto / xl_rpm if not np.isnan(rpm_auto) else float("nan")
        print(f"{sheet:<11} {fw}x{fh:<10} {str(period_ac):>10} {len(rp):>5} {med:>7.1f} {rpm_auto:>9.1f} {xl_rpm:>8.1f} {ratio:>7.2f}")

        ax = axes[idx, 2]
        ax.plot(frames, reds, "r-", lw=1, label=f"R ({len(rp)} pk)")
        ax.plot(frames, yels, "y-", lw=1)
        ax.plot(frames[rp], reds[rp], "rv", ms=5)
        ax.set_title(f"{sheet} | auto={rpm_auto:.0f} xl={xl_rpm:.0f} r={ratio:.2f}", fontsize=9)
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(alpha=0.3)
        ax.tick_params(labelsize=7)
        results[sheet] = {**info, "fine_roi": list(fine), "rpm_auto": rpm_auto, "rpm_xl": xl_rpm, "ratio": ratio}

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "fine_roi_v3.png"), dpi=80, bbox_inches="tight")
with open(os.path.join(OUT_DIR, "roi_config_final.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False, default=float)
print("\nsaved")
