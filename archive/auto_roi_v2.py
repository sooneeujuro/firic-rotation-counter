"""
ROI v2: '주기적으로 깜빡이는' 빨강 픽셀만 추출 → 정적 빨강 배경 제거.
"""
import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import json
import os

XLSX = r"C:\Users\USER\Firic_regular\For print.xlsx"
VIDEO_DIR = r"G:\FIRIC"
OUT_DIR = r"C:\Users\USER\Firic_regular\samples"

SHEETS = ["MARU", "CHEOEUM", "CHEOEUM_2", "ONNURI", "SAERO_1", "SAERO_2",
          "ONBADA", "ONBADA_2", "ONNARE", "ONNARE_2"]
PAD = 40
N_FRAMES = 90


def red_mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, (0, 100, 50), (10, 255, 255)) | cv2.inRange(hsv, (170, 100, 50), (180, 255, 255))


def auto_roi(video_path, init_frame):
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, init_frame)
    H, W = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    accum = np.zeros((H, W), dtype=np.uint16)
    n_read = 0
    sample = None
    for _ in range(N_FRAMES):
        ok, img = cap.read()
        if not ok:
            break
        if sample is None:
            sample = img.copy()
        accum += (red_mask(img) > 0).astype(np.uint16)
        n_read += 1
    cap.release()
    if n_read < 10:
        return None, sample, None
    lo = max(2, int(n_read * 0.02))
    hi = int(n_read * 0.5)
    flicker = ((accum >= lo) & (accum <= hi)).astype(np.uint8) * 255
    flicker = cv2.morphologyEx(flicker, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    num, labels, stats, _ = cv2.connectedComponentsWithStats(flicker)
    if num <= 1:
        return None, sample, accum
    areas = stats[1:, cv2.CC_STAT_AREA]
    valid = [(i + 1, areas[i]) for i in range(len(areas)) if 50 <= areas[i] <= 50000]
    if not valid:
        return None, sample, accum
    valid.sort(key=lambda t: -t[1])
    largest = valid[0][0]
    x, y, w, h = (int(stats[largest, cv2.CC_STAT_LEFT]),
                  int(stats[largest, cv2.CC_STAT_TOP]),
                  int(stats[largest, cv2.CC_STAT_WIDTH]),
                  int(stats[largest, cv2.CC_STAT_HEIGHT]))
    rx = max(0, x - PAD)
    ry = max(0, y - PAD)
    rw = min(W - rx, w + 2 * PAD)
    rh = min(H - ry, h + 2 * PAD)
    return (rx, ry, rw, rh), sample, accum


roi_config = {}
fig, axes = plt.subplots(5, 2, figsize=(18, 22))
axes = axes.flatten()

for idx, sheet in enumerate(SHEETS):
    raw = pd.read_excel(XLSX, sheet_name=sheet, header=None)
    video_name = str(raw.iloc[1, 2]).strip()
    init_frame = int(pd.to_numeric(raw.iloc[3, 0], errors="coerce"))
    video_path = os.path.join(VIDEO_DIR, video_name + ".mov")
    if not os.path.exists(video_path):
        continue
    roi, sample, _ = auto_roi(video_path, init_frame)
    rgb = cv2.cvtColor(sample, cv2.COLOR_BGR2RGB)
    axes[idx].imshow(rgb)
    if roi:
        x, y, w, h = roi
        axes[idx].add_patch(plt.Rectangle((x, y), w, h, fill=False, ec="lime", lw=3))
        roi_config[sheet] = {"video": video_name + ".mov", "init_frame": init_frame, "roi": list(roi)}
        axes[idx].set_title(f"{sheet} | init={init_frame} | ROI=({x},{y},{w},{h})", fontsize=10)
    else:
        roi_config[sheet] = {"video": video_name + ".mov", "init_frame": init_frame, "roi": None}
        axes[idx].set_title(f"{sheet} | NO ROI", fontsize=10, color="red")
    axes[idx].set_xticks(np.arange(0, 1921, 200))
    axes[idx].set_yticks(np.arange(0, 1081, 200))
    axes[idx].grid(color="cyan", alpha=0.3, lw=0.4)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "all_roi_v2.png"), dpi=80, bbox_inches="tight")
with open(os.path.join(OUT_DIR, "roi_config.json"), "w", encoding="utf-8") as f:
    json.dump(roi_config, f, indent=2, ensure_ascii=False)
print("Saved all_roi_v2.png + roi_config.json")
for s, v in roi_config.items():
    print(f"  {s}: ROI={v['roi']}")
