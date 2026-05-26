"""
Outlier 구간 영상 + 시계열 분석.
각 outlier row마다:
- 상단: ROI 영상 시퀀스 (구간 균등 8 frame)
- 중단: 빨강/노랑 시계열 + auto-detected peak + Excel init/final 마킹
- 하단: 짧은 mp4 저장 (사용자 직접 재생용)
"""
import cv2
import numpy as np
import json
import os
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, correlate

VIDEO_DIR = r"G:\FIRIC"
OUT_DIR = r"C:\Users\USER\Firic_regular\samples\outliers"
os.makedirs(OUT_DIR, exist_ok=True)
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


def estimate_period(signal, min_lag=3, max_lag=120):
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


for sheet, row_n, i0, i1, rot_xl, rpm_xl in OUTLIERS:
    info = cfg[sheet]
    video_path = os.path.join(VIDEO_DIR, info["video"])
    fx, fy, fw, fh = info["fine_roi"]

    pre = 15
    post = 15
    start = i0 - pre
    end = i1 + post

    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start)
    frames, reds, yels, imgs = [], [], [], []
    show_pad = 60
    for f in range(start, end + 1):
        ok, img = cap.read()
        if not ok:
            break
        roi_img = img[fy:fy + fh, fx:fx + fw]
        frames.append(f)
        reds.append(red_score(roi_img))
        yels.append(yellow_score(roi_img))
        crop = img[max(0, fy - show_pad):fy + fh + show_pad, max(0, fx - show_pad):fx + fw + show_pad]
        imgs.append(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
    cap.release()
    frames = np.array(frames)
    reds = np.array(reds)
    yels = np.array(yels)

    period_r = estimate_period(reds) or 30
    period_y = estimate_period(yels) or 30
    h_r = max(0.015, reds.mean() + 0.5 * reds.std())
    h_y = max(0.015, yels.mean() + 0.5 * yels.std())
    rp, _ = find_peaks(reds, height=h_r, distance=max(3, int(period_r * 0.6)))
    yp, _ = find_peaks(yels, height=h_y, distance=max(3, int(period_y * 0.6)))
    r_pf = frames[rp]
    y_pf = frames[yp]
    r_in = r_pf[(r_pf >= i0 - 3) & (r_pf <= i1 + 3)]
    y_in = y_pf[(y_pf >= i0 - 3) & (y_pf <= i1 + 3)]

    sample_indices = np.linspace(pre, pre + (i1 - i0), 8).astype(int)
    fig = plt.figure(figsize=(18, 9))
    gs = fig.add_gridspec(2, 8, height_ratios=[1, 1.5])

    for i, idx in enumerate(sample_indices):
        ax = fig.add_subplot(gs[0, i])
        ax.imshow(imgs[idx])
        ax.add_patch(plt.Rectangle((show_pad, show_pad), fw, fh, fill=False, ec="lime", lw=2))
        ax.set_title(f"f={frames[idx]}", fontsize=9)
        ax.axis("off")

    ax = fig.add_subplot(gs[1, :])
    ax.plot(frames, reds, "r-", lw=1.2, label=f"red ({len(r_in)} pk in row)")
    ax.plot(frames, yels, "y-", lw=1.2, label=f"yel ({len(y_in)} pk in row)")
    ax.plot(r_pf, reds[rp], "rv", ms=10, label="R peak")
    ax.plot(y_pf, yels[yp], "y^", ms=10, label="Y peak")
    ax.axvline(i0, color="g", ls="--", lw=2, label=f"Excel start ({i0})")
    ax.axvline(i1, color="b", ls="--", lw=2, label=f"Excel end ({i1})")
    rot_auto = len(r_in) - 1 if len(r_in) >= 2 else (len(y_in) - 1 if len(y_in) >= 2 else 0)
    t_xl = (i1 - i0) / FPS
    rpm_auto_from_peaks = (rot_auto / ((r_in[-1] - r_in[0]) / FPS) * 60) if len(r_in) >= 2 else float("nan")
    ax.set_title(f"{sheet} row {row_n} | frames {i0}-{i1} ({i1-i0}f, {t_xl:.2f}s) | "
                 f"Excel: {rot_xl} rot, {rpm_xl:.1f} RPM  vs  Auto: {rot_auto} rot, {rpm_auto_from_peaks:.1f} RPM",
                 fontsize=11)
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(alpha=0.3)
    ax.set_xlabel("Frame #")
    ax.set_ylabel("Score in fine ROI")

    plt.tight_layout()
    out_png = os.path.join(OUT_DIR, f"{sheet}_row{row_n:02d}.png")
    plt.savefig(out_png, dpi=95, bbox_inches="tight")
    plt.close()

    mp4_path = os.path.join(OUT_DIR, f"{sheet}_row{row_n:02d}.mp4")
    h, w = imgs[0].shape[:2]
    out_vid = cv2.VideoWriter(mp4_path, cv2.VideoWriter_fourcc(*"mp4v"), 10, (w, h))
    for i, im in enumerate(imgs):
        bgr = cv2.cvtColor(im, cv2.COLOR_RGB2BGR)
        cv2.rectangle(bgr, (show_pad, show_pad), (show_pad + fw, show_pad + fh), (0, 255, 0), 2)
        in_row = i0 <= frames[i] <= i1
        color = (0, 255, 255) if in_row else (200, 200, 200)
        cv2.putText(bgr, f"f={frames[i]}{' *' if in_row else ''}", (5, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        out_vid.write(bgr)
    out_vid.release()
    print(f"saved {sheet} row {row_n}: png + mp4 (Excel {rot_xl} rot vs Auto {rot_auto} rot)")

print(f"\nAll outputs in: {OUT_DIR}")
