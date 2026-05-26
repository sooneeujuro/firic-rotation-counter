"""
Fine ROI 자동 결정.
Coarse 안에서 빨강+노랑 깜빡임 mask 누적 → connected components → 가장 큰 cluster만 채택.
보통 카메라에 가까운 쪽이 더 크고 진하게 보이므로 한쪽만 자동 선택됨.
"""
import cv2
import numpy as np
import json
import os
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

VIDEO_DIR = r"G:\FIRIC"
OUT_DIR = r"C:\Users\USER\Firic_regular\samples"
N_FRAMES = 120
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
        return None, sample, None, None

    lo, hi = max(2, int(n * 0.02)), int(n * 0.6)
    flicker_r = (accum_r >= lo) & (accum_r <= hi)
    flicker_y = (accum_y >= lo) & (accum_y <= hi)
    flicker = (flicker_r | flicker_y).astype(np.uint8) * 255
    flicker = cv2.morphologyEx(flicker, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

    num, labels, stats, _ = cv2.connectedComponentsWithStats(flicker)
    if num <= 1:
        return None, sample, accum_r, accum_y
    areas = stats[1:, cv2.CC_STAT_AREA]
    valid_idx = [i for i in range(len(areas)) if 20 <= areas[i] <= cw * ch * 0.5]
    if not valid_idx:
        return None, sample, accum_r, accum_y
    valid_idx.sort(key=lambda i: -areas[i])
    largest = valid_idx[0] + 1

    fx, fy = int(stats[largest, cv2.CC_STAT_LEFT]), int(stats[largest, cv2.CC_STAT_TOP])
    fw, fh = int(stats[largest, cv2.CC_STAT_WIDTH]), int(stats[largest, cv2.CC_STAT_HEIGHT])
    rx = max(0, cx + fx - PAD)
    ry = max(0, cy + fy - PAD)
    rw = min(1920 - rx, fw + 2 * PAD)
    rh = min(1080 - ry, fh + 2 * PAD)
    return (rx, ry, rw, rh), sample, accum_r, accum_y


def red_score(roi):
    m = red_mask(roi)
    return float(m.sum()) / (roi.shape[0] * roi.shape[1] * 255)


def yellow_score(roi):
    m = yellow_mask(roi)
    return float(m.sum()) / (roi.shape[0] * roi.shape[1] * 255)


fig, axes = plt.subplots(10, 3, figsize=(20, 30))
results = {}

for idx, (sheet, info) in enumerate(cfg.items()):
    video_path = os.path.join(VIDEO_DIR, info["video"])
    init_f = info["init_frame"]
    coarse = info["coarse_roi"]

    fine, sample, accum_r, accum_y = auto_fine(video_path, init_f, coarse)
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
    axes[idx, 0].grid(color="cyan", alpha=0.3, lw=0.3)
    axes[idx, 0].tick_params(labelsize=7)

    if accum_r is not None:
        combined = (accum_r.astype(int) + accum_y.astype(int))
        axes[idx, 1].imshow(combined, cmap="hot", extent=(cx, cx + cw, cy + ch, cy))
        axes[idx, 1].set_title(f"{sheet} flicker heatmap (R+Y count)", fontsize=9)
        axes[idx, 1].tick_params(labelsize=7)
    else:
        axes[idx, 1].axis("off")

    if fine:
        fx, fy, fw, fh = fine
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, init_f)
        frames, reds, yels = [], [], []
        for i in range(150):
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
        rp, _ = find_peaks(reds, height=0.02, distance=3)
        yp, _ = find_peaks(yels, height=0.02, distance=3)
        ax = axes[idx, 2]
        ax.plot(frames, reds, "r-", lw=1, label=f"R ({len(rp)} pk)")
        ax.plot(frames, yels, "y-", lw=1, label=f"Y ({len(yp)} pk)")
        ax.plot(frames[rp], reds[rp], "rv", ms=5)
        ax.plot(frames[yp], yels[yp], "y^", ms=5)
        if len(rp) >= 2:
            med = float(np.median(np.diff(frames[rp])))
            rpm = 60 * FPS / med if med > 0 else 0
            ax.set_title(f"{sheet} fine | R period~{med:.1f}f, RPM~{rpm:.0f}", fontsize=10)
        else:
            ax.set_title(f"{sheet} fine | not enough", fontsize=10)
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(alpha=0.3)
        ax.tick_params(labelsize=7)
        results[sheet] = {
            "video": info["video"], "init_frame": init_f,
            "coarse_roi": coarse, "fine_roi": list(fine),
        }
    else:
        axes[idx, 2].axis("off")
        results[sheet] = {
            "video": info["video"], "init_frame": init_f,
            "coarse_roi": coarse, "fine_roi": None,
        }

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "fine_roi.png"), dpi=80, bbox_inches="tight")
with open(os.path.join(OUT_DIR, "roi_config_final.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("saved fine_roi.png + roi_config_final.json")
for s, v in results.items():
    print(f"  {s}: fine_roi={v['fine_roi']}")
