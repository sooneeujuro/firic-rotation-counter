"""
각 ROI 영역 zoom 이미지 (10개 시트별 ROI 영역만 확대해서 보기 쉽게).
"""
import cv2
import json
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

XLSX = r"C:\Users\USER\Firic_regular\For print.xlsx"
VIDEO_DIR = r"G:\FIRIC"
OUT_DIR = r"C:\Users\USER\Firic_regular\samples"

with open(os.path.join(OUT_DIR, "roi_config.json"), "r", encoding="utf-8") as f:
    cfg = json.load(f)

fig, axes = plt.subplots(5, 2, figsize=(16, 18))
axes = axes.flatten()

for idx, (sheet, info) in enumerate(cfg.items()):
    video_path = os.path.join(VIDEO_DIR, info["video"])
    init_f = info["init_frame"]
    roi = info["roi"]
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, init_f + 5)
    _, img = cap.read()
    cap.release()
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    if roi:
        x, y, w, h = roi
        pad = 80
        zx0 = max(0, x - pad)
        zy0 = max(0, y - pad)
        zx1 = min(1920, x + w + pad)
        zy1 = min(1080, y + h + pad)
        zoom = rgb[zy0:zy1, zx0:zx1]
        axes[idx].imshow(zoom, extent=(zx0, zx1, zy1, zy0))
        axes[idx].add_patch(plt.Rectangle((x, y), w, h, fill=False, ec="lime", lw=3))
        axes[idx].set_title(f"{sheet} | f={init_f} | ROI=({x},{y},{w},{h})", fontsize=11)
        step = 50
        axes[idx].set_xticks(np.arange(zx0 // step * step, zx1 + step, step))
        axes[idx].set_yticks(np.arange(zy0 // step * step, zy1 + step, step))
        axes[idx].grid(color="cyan", alpha=0.4, lw=0.4)
        axes[idx].tick_params(labelsize=7)
    else:
        axes[idx].imshow(rgb)
        axes[idx].set_title(f"{sheet} | NO ROI", color="red")
        axes[idx].axis("off")

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "roi_zoom_all.png"), dpi=85, bbox_inches="tight")
print("saved roi_zoom_all.png")
