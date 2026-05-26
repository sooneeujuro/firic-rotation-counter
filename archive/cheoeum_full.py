"""
CHEOEUM 시트 전체 27개 row 자동측정 vs 수동측정 비교.
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


def red_score(bgr_roi):
    hsv = cv2.cvtColor(bgr_roi, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, (0, 100, 50), (10, 255, 255))
    m2 = cv2.inRange(hsv, (170, 100, 50), (180, 255, 255))
    return float((m1 | m2).sum()) / (bgr_roi.shape[0] * bgr_roi.shape[1] * 255)


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
print(f"Processing frames {start}~{end} ({end - start + 1} frames)")

cap = cv2.VideoCapture(VIDEO)
cap.set(cv2.CAP_PROP_POS_FRAMES, start)
x, y, w, h = ROI
frames, scores = [], []
for f in range(start, end + 1):
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
print(f"Total peaks detected: {len(peak_frames)}")

results = []
for i, row in data.iterrows():
    init_f, final_f = row["init_frame"], row["final_frame"]
    mask = (peak_frames >= init_f - 3) & (peak_frames <= final_f + 3)
    in_peaks = peak_frames[mask]
    if len(in_peaks) >= 2:
        rot_auto = len(in_peaks) - 1
        time_auto = (in_peaks[-1] - in_peaks[0]) / FPS
        rpm_auto = (rot_auto / time_auto) * 60
    else:
        rot_auto = time_auto = rpm_auto = np.nan
    results.append({
        "row": i + 1,
        "init": init_f, "final": final_f,
        "rot_xl": row["rotation"], "rot_auto": rot_auto,
        "time_xl": row["time_s"], "time_auto": time_auto,
        "rpm_xl": row["rpm"], "rpm_auto": rpm_auto,
        "n_peaks": len(in_peaks),
    })
res = pd.DataFrame(results)
res["rpm_err_%"] = (res["rpm_auto"] - res["rpm_xl"]) / res["rpm_xl"] * 100
res["rot_match"] = (res["rot_auto"] == res["rot_xl"]).map({True: "OK", False: "x"})

print()
print(res.to_string(index=False,
                    formatters={
                        "rot_xl": "{:.0f}".format, "rot_auto": "{:.0f}".format,
                        "time_xl": "{:.3f}".format, "time_auto": "{:.3f}".format,
                        "rpm_xl": "{:.2f}".format, "rpm_auto": "{:.2f}".format,
                        "rpm_err_%": "{:+.2f}".format,
                    }))
print()
n_match = (res["rot_auto"] == res["rot_xl"]).sum()
print(f"Rotation match: {n_match}/{len(res)} ({n_match/len(res)*100:.0f}%)")
print(f"RPM error: mean={res['rpm_err_%'].abs().mean():.2f}%, max={res['rpm_err_%'].abs().max():.2f}%")

fig, axes = plt.subplots(2, 1, figsize=(16, 8))
axes[0].plot(frames, scores, "b-", lw=0.5, alpha=0.6)
axes[0].plot(peak_frames, scores[peaks], "rv", ms=5)
for _, row in data.iterrows():
    axes[0].axvline(row["init_frame"], color="g", alpha=0.15, lw=0.5)
axes[0].set_xlabel("Frame #")
axes[0].set_ylabel("Red score in ROI")
axes[0].set_title(f"{SHEET} full sequence | {len(peak_frames)} peaks | ROI={ROI}")
axes[0].grid(alpha=0.3)

axes[1].plot(res["row"], res["rpm_xl"], "go-", label="Excel (manual)", ms=8)
axes[1].plot(res["row"], res["rpm_auto"], "r^-", label="Auto detection", ms=6)
axes[1].set_xlabel("Row #")
axes[1].set_ylabel("RPM")
axes[1].set_title("Manual vs Auto RPM per row")
axes[1].legend()
axes[1].grid(alpha=0.3)

plt.tight_layout()
plt.savefig(f"{OUT_DIR}\\full_compare.png", dpi=100)
res.to_csv(f"{OUT_DIR}\\full_compare.csv", index=False)
print(f"\nsaved {OUT_DIR}\\full_compare.png")
print(f"saved {OUT_DIR}\\full_compare.csv")
