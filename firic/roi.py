"""Two-stage ROI selection.

Stage 1 (Coarse, manual): user drags a large box covering the whole
impeller rotation area — typically wide enough to include both the
near and far side of the rotation plane as seen from the ROV camera.

Stage 2 (Fine, automatic): within the coarse box, accumulate
red+yellow flicker over ~240 frames, compute a flicker score per pixel,
Gaussian-blur, and place a fixed-size ROI at the global maximum.

Why the flicker score? A pixel that is *always* red (e.g. a static
flag on the ROV) or *never* red has zero rotation information.
The maximum of p·(1−p) sits at p=0.5, exactly the regime of a marker
sweeping by periodically. Picking the global max (rather than all
clusters above a threshold) also automatically selects the near side
of the rotation, since the near marker is brighter / less smoke-veiled.
"""
from __future__ import annotations

import cv2
import numpy as np

from .detection import red_mask, yellow_mask


def auto_fine_roi(
    video_path: str,
    init_frame: int,
    coarse_roi: tuple[int, int, int, int],
    n_frames: int = 240,
    fine_w: int = 90,
    fine_h: int = 70,
    yellow_weight: float = 0.7,
    frame_size: tuple[int, int] = (1920, 1080),
) -> tuple[tuple[int, int, int, int] | None, np.ndarray | None, np.ndarray | None]:
    """Determine a fine ROI inside the user-provided coarse ROI.

    Parameters
    ----------
    video_path : str
        Path to the video file.
    init_frame : int
        First frame of the measurement segment (used as the analysis start).
    coarse_roi : (x, y, w, h)
        Coarse ROI in video-frame coordinates.
    n_frames : int
        Number of frames to accumulate. ~240 covers slow rotations (~17 RPM)
        for at least one full revolution.
    fine_w, fine_h : int
        Fixed fine-ROI size (px). Defaults are tuned to marker width.
    yellow_weight : float
        Weight for yellow channel in flicker map (default 0.7).
    frame_size : (W, H)
        Video frame size for boundary clipping.

    Returns
    -------
    fine_roi : (x, y, w, h) or None
    sample_frame : np.ndarray or None
        BGR image of the first frame (for visualization).
    flicker_map : np.ndarray or None
        2D float array of flicker weight within the coarse ROI.
    """
    W, H = frame_size
    cx, cy, cw, ch = coarse_roi
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, init_frame)
    accum = np.zeros((ch, cw), dtype=np.float32)
    sample = None
    n = 0
    for _ in range(n_frames):
        ok, img = cap.read()
        if not ok:
            break
        if sample is None:
            sample = img.copy()
        roi_img = img[cy:cy + ch, cx:cx + cw]
        accum += (red_mask(roi_img) > 0).astype(np.float32)
        accum += yellow_weight * (yellow_mask(roi_img) > 0).astype(np.float32)
        n += 1
    cap.release()
    if n < 10:
        return None, sample, None

    sat_ratio = accum / n
    flicker = sat_ratio * (1.0 - sat_ratio) * 4.0  # bell curve peaked at p=0.5
    flicker = np.clip(flicker, 0, 1)
    blurred = cv2.GaussianBlur(flicker, (15, 15), 0)

    py, px = np.unravel_index(int(np.argmax(blurred)), blurred.shape)
    fw = min(fine_w, cw)
    fh = min(fine_h, ch)
    fx_local = max(0, min(cw - fw, int(px) - fw // 2))
    fy_local = max(0, min(ch - fh, int(py) - fh // 2))
    rx = cx + fx_local
    ry = cy + fy_local
    rx = max(0, min(W - fw, rx))
    ry = max(0, min(H - fh, ry))
    return (int(rx), int(ry), int(fw), int(fh)), sample, blurred
