"""
Mismatch row 3 (11697-11743) 구간 디버깅.
- 그 구간 빨강 시계열 확대
- 마커가 정말 안 보이는지 sample frame 추출
"""
import cv2
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

VIDEO = r"G:\FIRIC\R2374_Zeus_2024-05-04-055112.mov"
ROI = (820, 350, 200, 130)
START, END = 11690, 11750
FPS = 30000 / 1001


def red_score(roi):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, (0, 100, 50), (10, 255, 255))
    m2 = cv2.inRange(hsv, (170, 100, 50), (180, 255, 255))
    return float((m1 | m2).sum()) / (roi.shape[0] * roi.shape[1] * 255)


def yellow_score(roi):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (15, 80, 80), (35, 255, 255))
    return float(m.sum()) / (roi.shape[0] * roi.shape[1] * 255)


cap = cv2.VideoCapture(VIDEO)
cap.set(cv2.CAP_PROP_POS_FRAMES, START)
x, y, w, h = ROI
frames, reds, yellows = [], [], []
sample_imgs = {}
for f in range(START, END + 1):
    ok, img = cap.read()
    if not ok:
        break
    frames.append(f)
    roi_img = img[y:y + h, x:x + w]
    reds.append(red_score(roi_img))
    yellows.append(yellow_score(roi_img))
    if f in (11697, 11705, 11713, 11720, 11728, 11735, 11743):
        sample_imgs[f] = cv2.cvtColor(roi_img, cv2.COLOR_BGR2RGB)
cap.release()
frames = np.array(frames)
reds = np.array(reds)
yellows = np.array(yellows)

fig = plt.figure(figsize=(16, 10))
gs = fig.add_gridspec(3, 7)

ax1 = fig.add_subplot(gs[0, :])
ax1.plot(frames, reds, "r-", label="red score", lw=1.5)
ax1.plot(frames, yellows, "y-", label="yellow score", lw=1.5)
ax1.axvline(11697, color="g", ls="--", alpha=0.5, label="row3 start (11697)")
ax1.axvline(11743, color="b", ls="--", alpha=0.5, label="row3 end (11743)")
ax1.set_title("CHEOEUM row 3 region: red + yellow scores")
ax1.set_xlabel("Frame #")
ax1.legend()
ax1.grid(alpha=0.3)

ax2 = fig.add_subplot(gs[1, :])
combo = reds + yellows
peaks, _ = find_peaks(combo, height=0.02, distance=4)
peak_frames = frames[peaks]
ax2.plot(frames, combo, "k-", lw=1)
ax2.plot(peak_frames, combo[peaks], "rv", ms=10, label=f"combined peaks ({len(peaks)})")
ax2.axvline(11697, color="g", ls="--", alpha=0.5)
ax2.axvline(11743, color="b", ls="--", alpha=0.5)
ax2.set_title(f"Red+Yellow combined: detected {len(peaks)} peaks (Excel says 3 rotations = ~3 red peaks expected)")
ax2.legend()
ax2.grid(alpha=0.3)

for i, (f, im) in enumerate(sorted(sample_imgs.items())):
    ax = fig.add_subplot(gs[2, i])
    ax.imshow(im)
    ax.set_title(f"f={f}")
    ax.axis("off")

plt.tight_layout()
plt.savefig(r"C:\Users\USER\Firic_regular\samples\CHEOEUM\debug_row3.png", dpi=100)
print(f"red peaks in [11694, 11746]:", peak_frames[(peak_frames>=11694)&(peak_frames<=11746)].tolist())
print(f"Excel row3: 11697-11743, 3 rotation")
print(f"If yellow+red gives 3 marker passes per rotation, expected combined peaks = ~3 rotations * 3 = ~9")
