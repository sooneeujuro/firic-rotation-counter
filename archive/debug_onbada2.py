"""ONBADA_2 디버깅 - 왜 peak가 거의 안 잡히는지."""
import cv2
import numpy as np
import json
import os
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

VIDEO_DIR = r"G:\FIRIC"
OUT_DIR = r"C:\Users\USER\Firic_regular\samples"

with open(os.path.join(OUT_DIR, "roi_config_final.json"), "r", encoding="utf-8") as f:
    cfg = json.load(f)

sheet = "ONBADA_2"
info = cfg[sheet]
print(f"{sheet} info:")
print(f"  video: {info['video']}")
print(f"  init: {info['init_frame']}")
print(f"  coarse: {info['coarse_roi']}")
print(f"  fine: {info['fine_roi']}")


def red_score(roi):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, (0, 100, 50), (10, 255, 255))
    m2 = cv2.inRange(hsv, (170, 100, 50), (180, 255, 255))
    return float((m1 | m2).sum()) / (roi.shape[0] * roi.shape[1] * 255)


def yellow_score(roi):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (15, 80, 80), (35, 255, 255))
    return float(m.sum()) / (roi.shape[0] * roi.shape[1] * 255)


fx, fy, fw, fh = info["fine_roi"]
start = info["init_frame"]
end = start + 700

cap = cv2.VideoCapture(os.path.join(VIDEO_DIR, info["video"]))
cap.set(cv2.CAP_PROP_POS_FRAMES, start)
frames, reds, yels = [], [], []
sample_imgs = []
for i in range(end - start):
    ok, img = cap.read()
    if not ok:
        break
    roi_img = img[fy:fy + fh, fx:fx + fw]
    frames.append(start + i)
    reds.append(red_score(roi_img))
    yels.append(yellow_score(roi_img))
    if i in [0, 100, 200, 300, 400, 500, 600]:
        sample_imgs.append((start + i, cv2.cvtColor(roi_img, cv2.COLOR_BGR2RGB), cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
cap.release()

frames = np.array(frames)
reds = np.array(reds)
yels = np.array(yels)

print(f"\nreds stats: min={reds.min():.4f}, max={reds.max():.4f}, mean={reds.mean():.4f}")
print(f"yels stats: min={yels.min():.4f}, max={yels.max():.4f}, mean={yels.mean():.4f}")

fig = plt.figure(figsize=(20, 12))
gs = fig.add_gridspec(3, 7)

ax1 = fig.add_subplot(gs[0, :])
ax1.plot(frames, reds, "r-", label="red", lw=1)
ax1.plot(frames, yels, "y-", label="yellow", lw=1)
ax1.set_title(f"{sheet} ROI={info['fine_roi']} - full series")
ax1.legend()
ax1.grid(alpha=0.3)

ax2 = fig.add_subplot(gs[1, :])
for f, _, full in sample_imgs:
    pass
ax2.plot(frames[:300], reds[:300], "r-", lw=1)
ax2.plot(frames[:300], yels[:300], "y-", lw=1)
ax2.set_title(f"first 300 frames")
ax2.grid(alpha=0.3)

for i, (f, roi_img, full) in enumerate(sample_imgs):
    ax = fig.add_subplot(gs[2, i])
    ax.imshow(full[fy:fy + fh + 40, max(0, fx - 40):fx + fw + 40])
    ax.add_patch(plt.Rectangle((40, 0), fw, fh, fill=False, ec="lime", lw=2))
    ax.set_title(f"f={f}", fontsize=9)
    ax.axis("off")

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "debug_onbada2.png"), dpi=85, bbox_inches="tight")
print(f"\nsaved debug_onbada2.png")
