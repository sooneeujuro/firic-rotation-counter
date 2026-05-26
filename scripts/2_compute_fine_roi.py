"""Step 2 — automatically determine the fine ROI within each coarse ROI.

Reads ``output/coarse_roi.json``, runs :func:`firic.auto_fine_roi`
per sheet, and writes ``output/roi_config.json`` with both coarse and
fine boxes. Also writes ``output/fine_roi_preview.png`` for visual
sanity check.
"""
from __future__ import annotations

import json
import os
import sys

import cv2
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from firic import auto_fine_roi  # noqa: E402

VIDEO_DIR = r"G:\FIRIC"
COARSE_PATH = os.path.join(ROOT, "output", "coarse_roi.json")
FINAL_PATH = os.path.join(ROOT, "output", "roi_config.json")
PREVIEW = os.path.join(ROOT, "output", "fine_roi_preview.png")


def main():
    with open(COARSE_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    results = {}
    n = len(cfg)
    cols = 2
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols * 2, figsize=(20, 4 * rows))
    axes = np.array(axes).reshape(rows, cols * 2)

    for i, (sheet, info) in enumerate(cfg.items()):
        r, c = divmod(i, cols)
        ax_img = axes[r, c * 2]
        ax_map = axes[r, c * 2 + 1]

        video_path = os.path.join(VIDEO_DIR, info["video"])
        fine, sample, fmap = auto_fine_roi(video_path, info["init_frame"], info["coarse_roi"])

        if sample is not None:
            rgb = cv2.cvtColor(sample, cv2.COLOR_BGR2RGB)
            cx, cy, cw, ch = info["coarse_roi"]
            pad = 30
            zx0, zy0 = max(0, cx - pad), max(0, cy - pad)
            zx1, zy1 = min(1920, cx + cw + pad), min(1080, cy + ch + pad)
            ax_img.imshow(rgb[zy0:zy1, zx0:zx1], extent=(zx0, zx1, zy1, zy0))
            ax_img.add_patch(plt.Rectangle((cx, cy), cw, ch, fill=False, ec="orange", lw=2))
            if fine:
                fx, fy, fw, fh = fine
                ax_img.add_patch(plt.Rectangle((fx, fy), fw, fh, fill=False, ec="lime", lw=3))
            ax_img.set_title(f"{sheet} fine={fine}", fontsize=9)
        if fmap is not None:
            cx, cy, cw, ch = info["coarse_roi"]
            ax_map.imshow(fmap, cmap="hot", extent=(cx, cx + cw, cy + ch, cy))
            ax_map.set_title(f"{sheet} flicker", fontsize=9)
        results[sheet] = {**info, "fine_roi": list(fine) if fine else None}

    for j in range(n, rows * cols):
        r, c = divmod(j, cols)
        axes[r, c * 2].axis("off")
        axes[r, c * 2 + 1].axis("off")

    plt.tight_layout()
    plt.savefig(PREVIEW, dpi=80, bbox_inches="tight")
    plt.close()

    with open(FINAL_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=float)
    print(f"saved {FINAL_PATH}")
    print(f"saved {PREVIEW}")
    for s, v in results.items():
        print(f"  {s}: fine_roi={v['fine_roi']}")


if __name__ == "__main__":
    main()
