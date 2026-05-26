"""Color-based marker detection in ROI.

Markers on the impeller (red / yellow / reflective) are detected by
HSV thresholding, then time-series peaks are found per marker color.
Robust period estimation via autocorrelation + smoke-aware
interpolation for partially occluded segments.
"""
from __future__ import annotations

import cv2
import numpy as np
from scipy.signal import find_peaks, correlate


def red_mask(img_bgr: np.ndarray) -> np.ndarray:
    """Binary mask for red pixels (hue wraps around 0/180)."""
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, (0, 100, 50), (10, 255, 255))
    m2 = cv2.inRange(hsv, (170, 100, 50), (180, 255, 255))
    return m1 | m2


def yellow_mask(img_bgr: np.ndarray) -> np.ndarray:
    """Binary mask for yellow pixels."""
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, (15, 80, 80), (35, 255, 255))


def _score(roi_bgr: np.ndarray, mask_fn) -> float:
    if roi_bgr.size == 0:
        return 0.0
    m = mask_fn(roi_bgr)
    return float(m.sum()) / (roi_bgr.shape[0] * roi_bgr.shape[1] * 255)


def red_score(roi_bgr: np.ndarray) -> float:
    """Fraction of red-classified pixels in the ROI (0..1)."""
    return _score(roi_bgr, red_mask)


def yellow_score(roi_bgr: np.ndarray) -> float:
    """Fraction of yellow-classified pixels in the ROI (0..1)."""
    return _score(roi_bgr, yellow_mask)


def estimate_period(signal: np.ndarray, min_lag: int = 3, max_lag: int = 200) -> int | None:
    """Estimate rotation period (in frames) via autocorrelation.

    Returns the lag of the first significant autocorrelation peak,
    or None if the signal has no detectable periodicity.
    """
    s = signal - signal.mean()
    if s.std() == 0:
        return None
    ac = correlate(s, s, mode="full")
    ac = ac[len(s) - 1:]
    if ac[0] <= 0:
        return None
    ac = ac / ac[0]
    peaks, _ = find_peaks(ac[min_lag:min(max_lag, len(ac))], height=0.15)
    if len(peaks) == 0:
        return None
    return int(peaks[0] + min_lag)


def smoke_aware_peaks(
    scores: np.ndarray,
    period: int,
    h_strong: float,
    h_weak: float,
    gap_factor: float = 1.5,
    window_factor: float = 0.3,
) -> tuple[np.ndarray, np.ndarray]:
    """Find peaks with smoke-occlusion recovery.

    Step 1: detect strong peaks above ``h_strong``.
    Step 2: where adjacent strong peaks are farther than ``period * gap_factor``,
            search the expected positions (start + k*period) within a window
            of ``period * window_factor`` for weak local maxima above ``h_weak``.
            Recovered peaks are returned separately for visualization.

    Returns
    -------
    all_peaks : ndarray
        Sorted array of strong + interpolated peak indices.
    interpolated : ndarray
        Indices added by the interpolation step (subset of all_peaks).
    """
    strong, _ = find_peaks(scores, height=h_strong, distance=max(3, int(period * 0.6)))
    if len(strong) < 2:
        return strong, np.array([], dtype=int)

    interp: list[int] = []
    gap_th = period * gap_factor
    for i in range(len(strong) - 1):
        gap = strong[i + 1] - strong[i]
        if gap <= gap_th:
            continue
        n_missing = round(gap / period) - 1
        for k in range(1, n_missing + 1):
            exp_pos = strong[i] + int(period * k)
            w = int(period * window_factor)
            lo = max(0, exp_pos - w)
            hi = min(len(scores), exp_pos + w)
            window = scores[lo:hi]
            if len(window) == 0:
                continue
            local_max_idx = lo + int(window.argmax())
            if scores[local_max_idx] < h_weak:
                continue
            too_close = any(
                abs(local_max_idx - p) < int(period * 0.4)
                for p in list(strong) + interp
            )
            if not too_close:
                interp.append(local_max_idx)

    all_pk = np.array(sorted(list(strong) + interp))
    return all_pk, np.array(interp, dtype=int)
