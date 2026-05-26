"""
각 시트의 Coarse ROI에서 첫 5초간 빨강/노랑 시계열 + ROI 이미지 → 한 figure에.
원형 인디케이터 앞뒤 둘다 보이는 패턴 진단용.
"""
import cv2
import numpy as np
import json
import os
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

XLSX = r"C:\Users\USER\Firic_regular\For print.xlsx"
VIDEO_DIR = r"G:\FIRIC"
OUT_DIR = r"C:\Users\USER\Firic_regular\samples"
N_FRAMES = 150
FPS = 30000 / 1001

with open(os.path.join(OUT_DIR, "coarse_roi.json"), "r", encoding="utf-8") as f:
    cfg = json.load(f)


def red_score(roi):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, (0, 100, 50), (10, 255, 255))
    m2 = cv2.inRange(hsv, (170, 100, 50), (180, 255, 255))
    return float((m1 | m2).sum()) / (roi.shape[0] * roi.shape[1] * 255)


def yellow_score(roi):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (15, 80, 80), (35, 255, 255))
    return float(m.sum()) / (roi.shape[0] * roi.shape[1] * 255)


fig, axes = plt.subplots(10, 2, figsize=(20, 28))

for idx, (sheet, info) in enumerate(cfg.items()):
    video_path = os.path.join(VIDEO_DIR, info["video"])
    init_f = info["init_frame"]
    x, y, w, h = info["coarse_roi"]

    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, init_f)
    frames, reds, yels = [], [], []
    sample = None
    for i in range(N_FRAMES):
        ok, img = cap.read()
        if not ok:
            break
        if sample is None:
            sample = img.copy()
        roi_img = img[y:y + h, x:x + w]
        frames.append(init_f + i)
        reds.append(red_score(roi_img))
        yels.append(yellow_score(roi_img))
    cap.release()
    frames = np.array(frames)
    reds = np.array(reds)
    yels = np.array(yels)

    rp, _ = find_peaks(reds, height=0.02, distance=3)
    yp, _ = find_peaks(yels, height=0.02, distance=3)

    rgb = cv2.cvtColor(sample, cv2.COLOR_BGR2RGB)
    axes[idx, 0].imshow(rgb[max(0, y - 30):y + h + 30, max(0, x - 30):x + w + 30],
                        extent=(max(0, x - 30), x + w + 30, y + h + 30, max(0, y - 30)))
    axes[idx, 0].add_patch(plt.Rectangle((x, y), w, h, fill=False, ec="lime", lw=3))
    axes[idx, 0].set_title(f"{sheet} | coarse=({x},{y},{w},{h})", fontsize=9)
    axes[idx, 0].grid(color="cyan", alpha=0.3, lw=0.3)
    axes[idx, 0].tick_params(labelsize=7)

    ax = axes[idx, 1]
    ax.plot(frames, reds, "r-", lw=1, label=f"red ({len(rp)} pk)")
    ax.plot(frames, yels, "y-", lw=1, label=f"yel ({len(yp)} pk)")
    ax.plot(frames[rp], reds[rp], "rv", ms=6)
    ax.plot(frames[yp], yels[yp], "y^", ms=6)
    if len(rp) >= 2:
        median_period_r = float(np.median(np.diff(frames[rp])))
        rpm_r = 60 * FPS / median_period_r if median_period_r > 0 else 0
        ax.set_title(f"{sheet} | R period~{median_period_r:.1f}f, RPM~{rpm_r:.0f}", fontsize=10)
    else:
        ax.set_title(f"{sheet} | not enough red peaks", fontsize=10)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(alpha=0.3)
    ax.set_xlabel("Frame #", fontsize=8)

plt.tight_layout()
out_path = os.path.join(OUT_DIR, "coarse_inspect.png")
plt.savefig(out_path, dpi=85, bbox_inches="tight")
print(f"saved {out_path}")
