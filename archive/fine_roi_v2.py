"""
Fine ROI v2: cluster width 제한 + 느린 회전 대응.
"""
import cv2
import numpy as np
import json
import os
import pandas as pd
from scipy.signal import find_peaks
import matplotlib.pyplot as plt

XLSX = r"C:\Users\USER\Firic_regular\For print.xlsx"
VIDEO_DIR = r"G:\FIRIC"
OUT_DIR = r"C:\Users\USER\Firic_regular\samples"
N_FRAMES = 240
FPS = 30000 / 1001
PAD = 8

with open(os.path.join(OUT_DIR, "coarse_roi.json"), "r", encoding="utf-8") as f:
    cfg = json.load(f)


def red_mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, (0, 100, 50), (10, 255, 255)) | cv2.inRange(hsv, (170, 100, 50), (180, 255, 255))


def yellow_mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, (15, 80, 80), (35, 255, 255))


def auto_fine(video_path, init_frame, coarse):
    cx, cy, cw, ch = coarse
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, init_frame)
    accum_r = np.zeros((ch, cw), dtype=np.uint16)
    accum_y = np.zeros((ch, cw), dtype=np.uint16)
    sample = None
    n = 0
    for _ in range(N_FRAMES):
        ok, img = cap.read()
        if not ok:
            break
        if sample is None:
            sample = img.copy()
        roi_img = img[cy:cy + ch, cx:cx + cw]
        accum_r += (red_mask(roi_img) > 0).astype(np.uint16)
        accum_y += (yellow_mask(roi_img) > 0).astype(np.uint16)
        n += 1
    cap.release()
    if n < 10:
        return None, sample, None

    lo = max(2, int(n * 0.02))
    hi = int(n * 0.8)
    flicker = ((accum_r >= lo) & (accum_r <= hi)) | ((accum_y >= lo) & (accum_y <= hi))
    flicker = (flicker.astype(np.uint8) * 255)
    flicker = cv2.morphologyEx(flicker, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

    num, labels, stats, centroids = cv2.connectedComponentsWithStats(flicker)
    if num <= 1:
        return None, sample, accum_r + accum_y

    areas = stats[1:, cv2.CC_STAT_AREA]
    valid = sorted([i for i in range(len(areas)) if 20 <= areas[i] <= cw * ch * 0.5],
                   key=lambda i: -areas[i])
    if not valid:
        return None, sample, accum_r + accum_y
    largest = valid[0] + 1

    fx = int(stats[largest, cv2.CC_STAT_LEFT])
    fy = int(stats[largest, cv2.CC_STAT_TOP])
    fw = int(stats[largest, cv2.CC_STAT_WIDTH])
    fh = int(stats[largest, cv2.CC_STAT_HEIGHT])

    max_w = int(cw * 0.4)
    if fw > max_w:
        cluster_mask = (labels == largest)
        mid_x = fx + fw // 2
        left_score = (accum_r + accum_y)[fy:fy + fh, fx:mid_x][cluster_mask[fy:fy + fh, fx:mid_x]].sum()
        right_score = (accum_r + accum_y)[fy:fy + fh, mid_x:fx + fw][cluster_mask[fy:fy + fh, mid_x:fx + fw]].sum()
        if left_score >= right_score:
            fw = max_w
        else:
            fx = fx + fw - max_w
            fw = max_w

    rx = max(0, cx + fx - PAD)
    ry = max(0, cy + fy - PAD)
    rw = min(1920 - rx, fw + 2 * PAD)
    rh = min(1080 - ry, fh + 2 * PAD)
    return (rx, ry, rw, rh), sample, accum_r + accum_y


def red_score(roi):
    m = red_mask(roi)
    return float(m.sum()) / (roi.shape[0] * roi.shape[1] * 255)


def yellow_score(roi):
    m = yellow_mask(roi)
    return float(m.sum()) / (roi.shape[0] * roi.shape[1] * 255)


results = {}
fig, axes = plt.subplots(10, 3, figsize=(20, 30))

print(f"{'Sheet':<11} {'fine_size':<12} {'R_peaks':>8} {'R_med':>7} {'RPM_auto':>9} {'RPM_xl':>8} {'ratio':>7}")
print("-" * 70)

for idx, (sheet, info) in enumerate(cfg.items()):
    video_path = os.path.join(VIDEO_DIR, info["video"])
    init_f = info["init_frame"]
    coarse = info["coarse_roi"]

    fine, sample, accum = auto_fine(video_path, init_f, coarse)
    rgb = cv2.cvtColor(sample, cv2.COLOR_BGR2RGB)

    cx, cy, cw, ch = coarse
    pad_show = 30
    zx0, zy0 = max(0, cx - pad_show), max(0, cy - pad_show)
    zx1, zy1 = min(1920, cx + cw + pad_show), min(1080, cy + ch + pad_show)
    axes[idx, 0].imshow(rgb[zy0:zy1, zx0:zx1], extent=(zx0, zx1, zy1, zy0))
    axes[idx, 0].add_patch(plt.Rectangle((cx, cy), cw, ch, fill=False, ec="orange", lw=2, label="coarse"))
    if fine:
        fx, fy, fw, fh = fine
        axes[idx, 0].add_patch(plt.Rectangle((fx, fy), fw, fh, fill=False, ec="lime", lw=3, label="fine"))
    axes[idx, 0].set_title(f"{sheet} | fine={fine}", fontsize=9)
    axes[idx, 0].legend(loc="lower right", fontsize=8)
    axes[idx, 0].tick_params(labelsize=7)

    if accum is not None:
        axes[idx, 1].imshow(accum, cmap="hot", extent=(cx, cx + cw, cy + ch, cy))
        axes[idx, 1].set_title(f"{sheet} flicker (R+Y)", fontsize=9)
        axes[idx, 1].tick_params(labelsize=7)

    raw = pd.read_excel(XLSX, sheet_name=sheet, header=None)
    xl_rpm = float(pd.to_numeric(raw.iloc[3, 4], errors="coerce"))

    if fine:
        fx, fy, fw, fh = fine
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, init_f)
        reds, yels, frames = [], [], []
        for i in range(180):
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
        rp, _ = find_peaks(reds, height=0.015, distance=3)
        yp, _ = find_peaks(yels, height=0.015, distance=3)
        med = float(np.median(np.diff(rp))) if len(rp) >= 2 else float("nan")
        rpm_auto = 60 * FPS / med if med > 0 else float("nan")
        ratio = rpm_auto / xl_rpm if not np.isnan(rpm_auto) else float("nan")
        print(f"{sheet:<11} {fw}x{fh:<10} {len(rp):>8} {med:>7.1f} {rpm_auto:>9.1f} {xl_rpm:>8.1f} {ratio:>7.2f}")

        ax = axes[idx, 2]
        ax.plot(frames, reds, "r-", lw=1, label=f"R ({len(rp)} pk)")
        ax.plot(frames, yels, "y-", lw=1, label=f"Y ({len(yp)} pk)")
        ax.plot(frames[rp], reds[rp], "rv", ms=5)
        ax.plot(frames[yp], yels[yp], "y^", ms=5)
        ax.set_title(f"{sheet} | RPM_auto={rpm_auto:.0f} vs xl={xl_rpm:.0f} (ratio={ratio:.2f})", fontsize=9)
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(alpha=0.3)
        ax.tick_params(labelsize=7)
        results[sheet] = {**info, "fine_roi": list(fine), "rpm_auto": rpm_auto, "rpm_xl": xl_rpm, "ratio": ratio}
    else:
        print(f"{sheet:<11} NO FINE ROI")
        results[sheet] = {**info, "fine_roi": None}

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "fine_roi_v2.png"), dpi=80, bbox_inches="tight")
with open(os.path.join(OUT_DIR, "roi_config_final.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False, default=float)
print("\nsaved fine_roi_v2.png + roi_config_final.json")
