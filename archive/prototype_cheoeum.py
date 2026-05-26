"""
CHEOEUM 1구간 prototype.
첫 row: frame 11635~11666 (2 rotation, RPM 116.01).
빠른 회전(15.5프레임/회전) + 검은 연기 자욱한 환경 검증.
"""
import cv2
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

VIDEO = r"G:\FIRIC\R2374_Zeus_2024-05-04-055112.mov"
ROI = (820, 350, 200, 130)
START_FRAME, END_FRAME = 11620, 11700
FPS = 30000 / 1001


def red_score(bgr_roi):
    hsv = cv2.cvtColor(bgr_roi, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, (0, 100, 50), (10, 255, 255))
    m2 = cv2.inRange(hsv, (170, 100, 50), (180, 255, 255))
    return float((m1 | m2).sum()) / (bgr_roi.shape[0] * bgr_roi.shape[1] * 255)


cap = cv2.VideoCapture(VIDEO)
cap.set(cv2.CAP_PROP_POS_FRAMES, START_FRAME)
x, y, w, h = ROI
frames, scores = [], []
for f in range(START_FRAME, END_FRAME + 1):
    ok, img = cap.read()
    if not ok:
        break
    frames.append(f)
    scores.append(red_score(img[y:y + h, x:x + w]))
cap.release()

frames = np.array(frames)
scores = np.array(scores)
peaks, _ = find_peaks(scores, height=0.02, distance=8)
peak_frames = frames[peaks]

fig, axes = plt.subplots(2, 1, figsize=(14, 8))
axes[0].plot(frames, scores, "b-", lw=1)
axes[0].plot(peak_frames, scores[peaks], "rv", ms=10, label=f"peaks ({len(peaks)})")
axes[0].axvline(11635, color="g", ls="--", alpha=0.5, label="row1 start (11635)")
axes[0].axvline(11666, color="r", ls="--", alpha=0.5, label="row1 end (11666)")
axes[0].axvline(11697, color="m", ls="--", alpha=0.3, label="row2 end (11697)")
axes[0].set_xlabel("Frame #")
axes[0].set_ylabel("Red pixel ratio in ROI")
axes[0].set_title(f"CHEOEUM frame {START_FRAME}-{END_FRAME} | ROI={ROI}")
axes[0].legend()
axes[0].grid(alpha=0.3)

cap = cv2.VideoCapture(VIDEO)
cap.set(cv2.CAP_PROP_POS_FRAMES, 11635)
_, sample = cap.read()
cap.release()
sample_rgb = cv2.cvtColor(sample, cv2.COLOR_BGR2RGB)
axes[1].imshow(sample_rgb)
axes[1].add_patch(plt.Rectangle((x, y), w, h, fill=False, ec="lime", lw=3))
axes[1].set_title("ROI on frame 11635")
axes[1].axis("off")

plt.tight_layout()
plt.savefig(r"C:\Users\USER\Firic_regular\samples\CHEOEUM\prototype_result.png", dpi=100)
print(f"Frames: {START_FRAME}-{END_FRAME}")
print(f"Peaks detected: {len(peaks)} @ {peak_frames.tolist()}")
if len(peak_frames) >= 2:
    period_frames = np.diff(peak_frames)
    period_s = period_frames / FPS
    rpm = 60 / period_s
    print(f"Inter-peak frames: {period_frames.tolist()}")
    print(f"Inter-peak RPM: {[f'{r:.2f}' for r in rpm]}")
print(f"Excel row1 (11635-11666): 2 rotation, 32 frames(/2 = 16/rot), RPM 116.01")
