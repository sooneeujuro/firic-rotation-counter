"""
Fine ROI 진단: 각 시트의 Fine ROI에서 RPM 추정 vs Excel 비교.
"""
import cv2
import numpy as np
import json
import os
import pandas as pd
from scipy.signal import find_peaks

XLSX = r"C:\Users\USER\Firic_regular\For print.xlsx"
VIDEO_DIR = r"G:\FIRIC"
OUT_DIR = r"C:\Users\USER\Firic_regular\samples"
N_FRAMES = 150
FPS = 30000 / 1001

with open(os.path.join(OUT_DIR, "roi_config_final.json"), "r", encoding="utf-8") as f:
    cfg = json.load(f)


def red_score(roi):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, (0, 100, 50), (10, 255, 255))
    m2 = cv2.inRange(hsv, (170, 100, 50), (180, 255, 255))
    return float((m1 | m2).sum()) / (roi.shape[0] * roi.shape[1] * 255)


print(f"{'Sheet':<11} {'fine_size':<12} {'R_peaks':>8} {'R_med':>7} {'RPM_auto':>9} {'RPM_xl':>8} {'ratio':>7}")
print("-" * 70)
for sheet, info in cfg.items():
    if not info["fine_roi"]:
        continue
    fx, fy, fw, fh = info["fine_roi"]
    init_f = info["init_frame"]
    raw = pd.read_excel(XLSX, sheet_name=sheet, header=None)
    xl_rpm = float(pd.to_numeric(raw.iloc[3, 4], errors="coerce"))

    cap = cv2.VideoCapture(os.path.join(VIDEO_DIR, info["video"]))
    cap.set(cv2.CAP_PROP_POS_FRAMES, init_f)
    reds = []
    for _ in range(N_FRAMES):
        ok, img = cap.read()
        if not ok:
            break
        reds.append(red_score(img[fy:fy + fh, fx:fx + fw]))
    cap.release()
    reds = np.array(reds)
    rp, _ = find_peaks(reds, height=0.015, distance=3)
    if len(rp) >= 2:
        med = float(np.median(np.diff(rp)))
        rpm_auto = 60 * FPS / med
        ratio = rpm_auto / xl_rpm
    else:
        med = rpm_auto = ratio = float("nan")
    print(f"{sheet:<11} {fw}x{fh:<10} {len(rp):>8} {med:>7.1f} {rpm_auto:>9.1f} {xl_rpm:>8.1f} {ratio:>7.2f}")
