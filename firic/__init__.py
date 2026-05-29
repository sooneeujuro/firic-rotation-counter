"""firic — automated rotation counting from ROV underwater flowmeter videos."""
__version__ = "0.1.0"

from .detection import (
    red_score, yellow_score,
    red_mask, yellow_mask,
    estimate_period,
    smoke_aware_peaks,
)
from .roi import auto_fine_roi
from .pipeline import process_sheet, run_batch, read_video_fps

__all__ = [
    "red_score", "yellow_score", "red_mask", "yellow_mask",
    "estimate_period", "smoke_aware_peaks",
    "auto_fine_roi",
    "process_sheet", "run_batch", "read_video_fps",
]
