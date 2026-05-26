"""
CHEOEUM v2: 빨강+노랑 combined peak로 robustness 강화.
"""
import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

XLSX = r"C:\Users\USER\Firic_regular\For print.xlsx"
VIDEO = r"G:\FIRIC\R2374_Zeus_2024-05-04-055112.mov"
ROI = (820, 350, 200, 130)
SHEET = "CHEOEUM"
FPS = 30000 / 1001
OUT_DIR = r"C:\Users\USER\Firic_regular\samples\CHEOEUM"
MERGE_GAP = 4


def red_score(roi):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, (0, 100, 50), (10, 255, 255))
    m2 = cv2.inRange(hsv, (170, 100, 50), (180, 255, 255))
    return float((m1 | m2).sum()) / (roi.shape[0] * roi.shape[1] * 255)


def yellow_score(roi):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (15, 80, 80), (35, 255, 255))
    return float(m.sum()) / (roi.shape[0] * roi.shape[1] * 255)


raw = pd.read_excel(XLSX, sheet_name=SHEET, header=None)
data = raw.iloc[3:, :6].reset_index(drop=True)
data.columns = ["init_frame", "final_frame", "time_s", "rotation", "rpm", "timestamp"]
for c in data.columns:
    data[c] = pd.to_numeric(data[c], errors="coerce")
data = data.dropna(subset=["init_frame", "final_frame"]).reset_index(drop=True)
data["init_frame"] = data["init_frame"].astype(int)
data["final_frame"] = data["final_frame"].astype(int)

start = int(data["init_frame"].min()) - 10
end = int(data["final_frame"].max()) + 10

cap = cv2.VideoCapture(VIDEO)
cap.set(cv2.CAP_PROP_POS_FRAMES, start)
x, y, w, h = ROI
frames, reds, yels = [], [], []
for f in range(start, end + 1):
    ok, img = cap.read()
    if not ok:
        break
    frames.append(f)
    roi_img = img[y:y + h, x:x + w]
    reds.append(red_score(roi_img))
    yels.append(yellow_score(roi_img))
cap.release()
frames = np.array(frames)
reds = np.array(reds)
yels = np.array(yels)

r_peaks, _ = find_peaks(reds, height=0.02, distance=4)
y_peaks, _ = find_peaks(yels, height=0.02, distance=4)
r_pf = frames[r_peaks]
y_pf = frames[y_peaks]

all_p = sorted(list(r_pf) + list(y_pf))
merged = []
for p in all_p:
    if not merged or p - merged[-1] >= MERGE_GAP:
        merged.append(p)
merged = np.array(merged)
print(f"Red peaks: {len(r_pf)}, Yellow peaks: {len(y_pf)}, Combined merged: {len(merged)}")

results = []
for i, row in data.iterrows():
    init_f, final_f = row["init_frame"], row["final_frame"]
    in_p = merged[(merged >= init_f - 3) & (merged <= final_f + 3)]
    if len(in_p) >= 3:
        rot_auto = (len(in_p) - 1) / 2.0
        time_auto = (in_p[-1] - in_p[0]) / FPS
        rpm_auto = (rot_auto / time_auto) * 60
    elif len(in_p) >= 2:
        rot_auto = (len(in_p) - 1) / 2.0
        time_auto = (in_p[-1] - in_p[0]) / FPS
        rpm_auto = (rot_auto / time_auto) * 60
    else:
        rot_auto = time_auto = rpm_auto = np.nan
    results.append({
        "row": i + 1, "init": init_f, "final": final_f,
        "rot_xl": row["rotation"], "rot_auto": rot_auto,
        "rpm_xl": row["rpm"], "rpm_auto": rpm_auto,
        "n_peaks": len(in_p),
    })
res = pd.DataFrame(results)
res["rpm_err_%"] = (res["rpm_auto"] - res["rpm_xl"]) / res["rpm_xl"] * 100
res["rot_diff"] = res["rot_auto"] - res["rot_xl"]

print()
print(res.to_string(index=False,
                    formatters={
                        "rot_xl": "{:.0f}".format, "rot_auto": "{:.1f}".format,
                        "rpm_xl": "{:.2f}".format, "rpm_auto": "{:.2f}".format,
                        "rpm_err_%": "{:+.2f}".format, "rot_diff": "{:+.1f}".format,
                    }))
print()
n_match = (res["rot_auto"].round() == res["rot_xl"]).sum()
print(f"Rotation match (rounded): {n_match}/{len(res)} ({n_match/len(res)*100:.0f}%)")
print(f"RPM error: mean={res['rpm_err_%'].abs().mean():.2f}%, max={res['rpm_err_%'].abs().max():.2f}%")

fig, axes = plt.subplots(2, 1, figsize=(16, 8))
axes[0].plot(frames, reds, "r-", lw=0.6, alpha=0.7, label="red")
axes[0].plot(frames, yels, "y-", lw=0.6, alpha=0.7, label="yellow")
axes[0].plot(r_pf, reds[r_peaks], "rv", ms=5)
axes[0].plot(y_pf, yels[y_peaks], "y^", ms=5)
axes[0].plot(merged, np.full_like(merged, 0.2, dtype=float), "k|", ms=10, label=f"merged ({len(merged)})")
axes[0].set_title(f"{SHEET} red+yellow combined")
axes[0].legend()
axes[0].grid(alpha=0.3)

axes[1].plot(res["row"], res["rpm_xl"], "go-", label="Excel (manual)", ms=8)
axes[1].plot(res["row"], res["rpm_auto"], "r^-", label="Auto (R+Y)", ms=6)
axes[1].set_xlabel("Row #")
axes[1].set_ylabel("RPM")
axes[1].legend()
axes[1].grid(alpha=0.3)

plt.tight_layout()
plt.savefig(f"{OUT_DIR}\\v2_compare.png", dpi=100)
res.to_csv(f"{OUT_DIR}\\v2_compare.csv", index=False)
print(f"\nsaved {OUT_DIR}\\v2_compare.png")
