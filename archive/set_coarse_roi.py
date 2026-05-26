"""
2단 ROI Step 1: Coarse ROI 인터랙티브 지정.
영상마다 첫 측정 frame 띄움 → 마우스 드래그로 박스 → SPACE/ENTER 확정 → c 누르면 다음 영상 → ESC 전체 종료.

사용법:
  python set_coarse_roi.py

조작:
  - 마우스 드래그: 박스 그리기
  - SPACE 또는 ENTER: 확정하고 다음 영상
  - c: 현재 박스 취소하고 다시 그리기
  - ESC: 전체 종료
"""
import cv2
import json
import os
import pandas as pd

XLSX = r"C:\Users\USER\Firic_regular\For print.xlsx"
VIDEO_DIR = r"G:\FIRIC"
OUT_DIR = r"C:\Users\USER\Firic_regular\samples"
CONFIG_PATH = os.path.join(OUT_DIR, "coarse_roi.json")

SHEETS = ["MARU", "CHEOEUM", "CHEOEUM_2", "ONNURI", "SAERO_1", "SAERO_2",
          "ONBADA", "ONBADA_2", "ONNARE", "ONNARE_2"]

existing = {}
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        existing = json.load(f)
    print(f"기존 설정 로드: {len(existing)}개 시트")

config = dict(existing)

for sheet in SHEETS:
    if sheet in config and config[sheet].get("roi"):
        ans = input(f"{sheet}: 기존 ROI={config[sheet]['roi']} 있음. 다시? (y/N): ").strip().lower()
        if ans != "y":
            continue

    raw = pd.read_excel(XLSX, sheet_name=sheet, header=None)
    video_name = str(raw.iloc[1, 2]).strip()
    init_frame = int(pd.to_numeric(raw.iloc[3, 0], errors="coerce"))
    video_path = os.path.join(VIDEO_DIR, video_name + ".mov")

    if not os.path.exists(video_path):
        print(f"  ! 영상 없음: {video_path}")
        continue

    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, init_frame + 10)
    ok, img = cap.read()
    cap.release()
    if not ok:
        print(f"  ! 프레임 읽기 실패: {sheet}")
        continue

    win_name = f"[{sheet}] {video_name} | f={init_frame} | drag big box covering whole rotation area"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, 1280, 720)
    roi = cv2.selectROI(win_name, img, showCrosshair=True, fromCenter=False)
    cv2.destroyAllWindows()

    x, y, w, h = roi
    if w == 0 or h == 0:
        print(f"  - {sheet}: 스킵 (박스 없음)")
        continue

    config[sheet] = {
        "video": video_name + ".mov",
        "init_frame": init_frame,
        "coarse_roi": [int(x), int(y), int(w), int(h)],
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"  + {sheet}: coarse_roi=({x},{y},{w},{h}) saved")

print(f"\n완료! {CONFIG_PATH}에 저장됨.")
for s, v in config.items():
    print(f"  {s}: {v.get('coarse_roi')}")
