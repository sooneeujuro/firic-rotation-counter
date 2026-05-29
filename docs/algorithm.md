# Algorithm notes

## Problem

An ROV is parked next to a hydrothermal vent. A flowmeter mounted on
the ROV contains a free-spinning impeller, and an indicator wheel
attached to the impeller carries three markers — one red, one yellow,
one reflective. The wheel rotates inside a metal cage in the camera's
field of view.

To measure flow, an operator picks a 30-second video segment and,
frame by frame, records the frame numbers at which the same marker
returns to the same point in the view. One round trip is one rotation.
Multiple rows per segment let the operator track instantaneous RPM.

The goal of this project is to reproduce that workflow automatically
from the same videos, at the same frame resolution.

## Why a two-stage ROI

The natural single ROI — "the small patch where the marker is going to
appear" — has two failure modes:

1. **Too narrow for fast rotations.** The marker sweeps past in fewer
   frames than the sampling rate can resolve, so peaks become noisy or
   disappear.
2. **Too wide for slow rotations.** The marker is in the ROI for many
   consecutive frames, peaks broaden, peak-finding gets unstable, and
   the chance of catching unrelated objects (smoke, particulates) goes up.

The marker's speed in pixels per frame depends on the rotation rate,
which is exactly what we are trying to measure. Chicken-and-egg.

So the pipeline splits the choice in two:

- **Coarse ROI**: the operator drags a generous box around the whole
  rotation plane. Width and shape don't matter much.
- **Fine ROI**: inside the coarse box, the algorithm chooses a small
  fixed-size box (90 × 70 px) at the most informative location.

## How the fine ROI is chosen

For every pixel in the coarse box, accumulate over ~240 frames how
often it is classified as red or yellow. Convert the count to a ratio
`p` in [0, 1], then compute a **flicker weight**:

```
flicker = 4 · p · (1 − p)        # peaked at p = 0.5
```

- A pixel that is *always* red (`p = 1`) contributes zero. Static red
  features like an SDS flag on the ROV are filtered out automatically.
- A pixel that is *never* red (`p = 0`) also contributes zero.
- A pixel that flickers at roughly 50 % occupancy contributes the most.
  That is exactly the regime of a marker sweeping past periodically.

A 15 × 15 Gaussian blur smooths the map, and the fine ROI is placed
centered on the global maximum. Because the camera's near side is
usually brighter and less occluded by smoke than the far side, the
global maximum reliably lands on the near side — automatically
preventing the "both sides of the rotation get counted" double-detection
that would otherwise inflate RPM by 2×.

## Peak detection with smoke awareness

For each color channel, score series are computed over the whole
measurement span. Naïve peak detection (`scipy.signal.find_peaks`) with
a fixed distance fails in two ways:

- Slow rotations get false peaks from noise inside long visibility
  windows.
- Smoke occludes the marker for a fraction of a rotation, deleting the
  expected peak.

**Step 1** — estimate the rotation period from autocorrelation of the
score series. Set `find_peaks` distance to `0.6 × period`. This adapts
to whatever speed the rotation actually has, without prior knowledge.

**Step 2** — detect *strong* peaks above a dynamic threshold
(`mean + 0.5·std`).

**Step 3** — wherever two adjacent strong peaks are separated by more
than `1.5 × period`, the gap probably contains missed peaks. At each
expected position (`previous + k·period`), search a window of
`±0.3 × period` for the local maximum and accept it if it crosses a
*weak* threshold (≈ 30 % of the strong one). These recovered peaks are
tagged separately so plots can show them.

The net effect:

- Visible rotations → strong peaks pick them up.
- Smoke obscures a marker briefly → weak peak above the floor → recovered.
- Smoke fully blocks the marker → no peak above even the weak threshold
  → the rotation is reported as unknown, not invented.

## Row matching

Each Excel row gives `(init_frame, final_frame, rotation_xl, rpm_xl)`
plus a sheet-level `indicator` of R or Y for which color the operator
counted. The algorithm:

1. Picks the primary peak channel from `indicator`.
2. Counts primary peaks in `[init − tol, final + tol]` where
   `tol = max(3, 0.25 · period)`. This window is large enough to
   absorb sub-frame jitter without bleeding into the next row.
3. If primary peaks ≥ 2: `rotation_auto = n − 1`,
   `time_auto = (last − first) / fps`,
   `rpm_auto = rotation_auto / time_auto · 60`.
4. Fallback: combined R + Y peaks (rotation = (n − 1) / 2,
   assuming one of each color passes per rotation).
5. Last fallback: divide the row span by the estimated period.

The output preserves which fallback fired in the `src` column
(R / Y / R+Y / P-est) so partial-success rows are auditable.

The frame rate in step 3 is read from each video's container
(`cv2.CAP_PROP_FPS`), not assumed. RPM is linear in fps, so a wrong
constant would bias every value by the same percentage. All ten clips in
the validation set are constant-frame-rate 30000/1001 ≈ 29.97 fps, but the
pipeline reads it per file so footage from a different camera works
unchanged.

## Validation

Across 11 sheets and 232 rows:

- 224 rows match the manual rotation count exactly.
- Median row has zero RPM difference.
- The eight mismatched rows split into:
  - **4 fully-occluded** (CHEOEUM rows 3, 8, 20, 26): even weak peaks
    are absent. The algorithm correctly refuses to extrapolate.
  - **3 partially-occluded** (ONBADA rows 3, 5, 14): weak signal recovered
    one rotation but missed others.
  - **1 sub-frame timing** spread across CHEOEUM_2's 1-rotation rows
    (±1 frame in 12 frames = ±11.5 RPM, independent of detection).

These are properties of the videos, not the algorithm.
