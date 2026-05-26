"""
CHEOEUM 영상 frame 11635(빨강 peak 추정)에 grid + 추정 ROI 그려서 보여주기.
사용자가 ROI 위치 확인할 수 있게.
"""
import cv2
import matplotlib.pyplot as plt
import numpy as np

VIDEO = r"G:\FIRIC\R2374_Zeus_2024-05-04-055112.mov"
PEAK_FRAME = 11635
ROI_GUESS = (820, 350, 200, 130)

cap = cv2.VideoCapture(VIDEO)
cap.set(cv2.CAP_PROP_POS_FRAMES, PEAK_FRAME)
_, img = cap.read()
cap.release()
rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

fig, axes = plt.subplots(1, 2, figsize=(20, 6))

axes[0].imshow(rgb)
x, y, w, h = ROI_GUESS
axes[0].add_patch(plt.Rectangle((x, y), w, h, fill=False, ec="lime", lw=3, label=f"ROI guess ({x},{y},{w},{h})"))
axes[0].set_title(f"CHEOEUM frame {PEAK_FRAME} (1920x1080)")
axes[0].set_xticks(np.arange(0, 1921, 100))
axes[0].set_yticks(np.arange(0, 1081, 100))
axes[0].grid(color="cyan", alpha=0.4, lw=0.5)
axes[0].legend(loc="lower right")

zoom = rgb[200:600, 600:1200]
axes[1].imshow(zoom, extent=(600, 1200, 600, 200))
axes[1].add_patch(plt.Rectangle((x, y), w, h, fill=False, ec="lime", lw=3))
axes[1].set_title("Zoom: indicator area (x=600-1200, y=200-600)")
axes[1].set_xticks(np.arange(600, 1201, 50))
axes[1].set_yticks(np.arange(200, 601, 50))
axes[1].grid(color="cyan", alpha=0.4, lw=0.5)

plt.tight_layout()
plt.savefig(r"C:\Users\USER\Firic_regular\samples\CHEOEUM\roi_overview.png", dpi=100, bbox_inches="tight")
print("saved")
