"""
ROI 위치 시각화 — 현재 ROI(720,200,160,120)가 빨강 peak 프레임에서 어디에 위치하는지.
사용자가 정확한 ROI 좌표 짚어줄 수 있게 가이드 좌표축 추가.
"""
import cv2
import matplotlib.pyplot as plt
import numpy as np

VIDEO = r"G:\FIRIC\R2370_Zeus_2024-05-01-020722.mov"
ROI = (720, 200, 160, 120)
PEAK_FRAME = 3332

cap = cv2.VideoCapture(VIDEO)
cap.set(cv2.CAP_PROP_POS_FRAMES, PEAK_FRAME)
_, img = cap.read()
cap.release()
rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

fig, axes = plt.subplots(1, 2, figsize=(20, 6))

axes[0].imshow(rgb)
x, y, w, h = ROI
axes[0].add_patch(plt.Rectangle((x, y), w, h, fill=False, ec="lime", lw=3, label=f"current ROI ({x},{y},{w},{h})"))
axes[0].set_title(f"Full frame {PEAK_FRAME} (1920x1080) with current ROI")
axes[0].set_xticks(np.arange(0, 1921, 100))
axes[0].set_yticks(np.arange(0, 1081, 100))
axes[0].grid(color="cyan", alpha=0.4, lw=0.5)
axes[0].legend(loc="lower right")

zoom = rgb[100:500, 600:1200]
axes[1].imshow(zoom, extent=(600, 1200, 500, 100))
axes[1].add_patch(plt.Rectangle((x, y), w, h, fill=False, ec="lime", lw=3))
axes[1].set_title("Zoom: indicator area (x=600-1200, y=100-500)")
axes[1].set_xticks(np.arange(600, 1201, 50))
axes[1].set_yticks(np.arange(100, 501, 50))
axes[1].grid(color="cyan", alpha=0.4, lw=0.5)

plt.tight_layout()
plt.savefig(r"C:\Users\USER\Firic_regular\samples\MARU\roi_overview.png", dpi=100, bbox_inches="tight")
print("saved roi_overview.png")
