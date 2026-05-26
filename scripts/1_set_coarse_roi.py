"""Step 1 — interactively define the coarse ROI for each sheet.

For every sheet listed in SHEETS, this script:
  - reads the matching video filename from the Excel sheet metadata,
  - opens the first measurement frame (init_frame + 10) in a window,
  - lets you drag a rectangle around the *whole rotation area* of
    the impeller (wide enough that the marker passes through it once
    per revolution — but you don't need to make it tight; the fine
    ROI is computed automatically in step 2),
  - saves coordinates to OUT/coarse_roi.json.

Controls (cv2.selectROI):
  - drag with the mouse to draw a box
  - SPACE / ENTER to confirm and move to the next video
  - c to redraw the current box
  - ESC to abort
"""
from __future__ import annotations

import json
import os
import sys

import cv2
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

XLSX = os.path.join(ROOT, "data", "For print.xlsx")
VIDEO_DIR = r"G:\FIRIC"
OUT_PATH = os.path.join(ROOT, "output", "coarse_roi.json")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

SHEETS = ["MARU", "CHEOEUM", "CHEOEUM_2", "ONNURI", "SAERO_1", "SAERO_2",
          "ONBADA", "ONBADA_2", "ONNARE", "ONNARE_2"]


def main():
    existing = {}
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)
        print(f"Loaded {len(existing)} existing entries from {OUT_PATH}")

    config = dict(existing)
    for sheet in SHEETS:
        if sheet in config and config[sheet].get("coarse_roi"):
            ans = input(f"{sheet}: existing roi={config[sheet]['coarse_roi']}. Redo? (y/N): ").strip().lower()
            if ans != "y":
                continue

        raw = pd.read_excel(XLSX, sheet_name=sheet, header=None)
        video_name = str(raw.iloc[1, 2]).strip()
        init_frame = int(pd.to_numeric(raw.iloc[3, 0], errors="coerce"))
        video_path = os.path.join(VIDEO_DIR, video_name + ".mov")

        if not os.path.exists(video_path):
            print(f"  ! missing: {video_path}")
            continue

        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, init_frame + 10)
        ok, img = cap.read()
        cap.release()
        if not ok:
            print(f"  ! cannot read frame: {sheet}")
            continue

        win = f"[{sheet}] {video_name} f={init_frame} — drag a box around the rotation area"
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win, 1280, 720)
        roi = cv2.selectROI(win, img, showCrosshair=True, fromCenter=False)
        cv2.destroyAllWindows()

        x, y, w, h = roi
        if w == 0 or h == 0:
            print(f"  - {sheet}: skipped (empty box)")
            continue

        config[sheet] = {
            "video": video_name + ".mov",
            "init_frame": init_frame,
            "coarse_roi": [int(x), int(y), int(w), int(h)],
        }
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"  + {sheet}: coarse_roi=({x},{y},{w},{h}) saved")

    print(f"\nDone. Output: {OUT_PATH}")


if __name__ == "__main__":
    main()
