"""Visualization helpers for ROI placement and comparison plots."""
from __future__ import annotations

import os
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_vent_summary(all_results: dict, out_path: str | None = None,
                      dpi: int = 110, log_y: bool | None = None):
    """One-glance summary across multiple measurement segments.

    Bar chart of per-sheet mean auto-RPM with std as error bar, sorted
    by ascending mean. If `log_y` is None, auto-enables log scale when the
    max/min ratio is > 5 (typical when slow and fast vents coexist).

    Returns the matplotlib Figure (also saves to `out_path` if provided).
    """
    rows = []
    for sheet, (res, trace) in all_results.items():
        valid = res.dropna(subset=["rpm_auto"])
        if len(valid) == 0:
            continue
        rows.append({
            "sheet": sheet,
            "mean": float(valid["rpm_auto"].mean()),
            "std": float(valid["rpm_auto"].std(ddof=0)) if len(valid) > 1 else 0.0,
            "min": float(valid["rpm_auto"].min()),
            "max": float(valid["rpm_auto"].max()),
            "indicator": trace.get("indicator", ""),
        })
    if not rows:
        return None
    df = pd.DataFrame(rows).sort_values("mean").reset_index(drop=True)

    n = len(df)
    fig, ax = plt.subplots(figsize=(max(6, 0.6 * n + 3), 5))
    colors = ["#4C78A8" if ind == "R" else "#F58518" for ind in df["indicator"]]
    bars = ax.bar(df["sheet"], df["mean"], yerr=df["std"], capsize=4,
                  color=colors, edgecolor="black", linewidth=0.6, alpha=0.85)
    for b, m in zip(bars, df["mean"]):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                f"{m:.1f}", ha="center", va="bottom", fontsize=9)

    if log_y is None:
        log_y = (df["mean"].max() / max(df["mean"].min(), 1e-9)) > 5
    if log_y:
        ax.set_yscale("log")
    ax.set_ylabel("Mean RPM (auto, ± SD)")
    ax.set_title(f"Per-segment summary  (n = {n})")
    ax.tick_params(axis="x", rotation=30)
    ax.grid(True, axis="y", alpha=0.3)
    from matplotlib.patches import Patch
    legend_items = [
        Patch(facecolor="#4C78A8", edgecolor="black", label="Indicator R"),
        Patch(facecolor="#F58518", edgecolor="black", label="Indicator Y"),
    ]
    ax.legend(handles=legend_items, loc="upper left", fontsize=9)
    plt.tight_layout()
    if out_path:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        plt.savefig(out_path, dpi=dpi, bbox_inches="tight")
    return fig


def plot_vent_boxplot(all_results: dict, out_path: str | None = None, dpi: int = 110):
    """Per-vent RPM distribution boxplot. For 'rich' reports."""
    data, labels, indicators = [], [], []
    for sheet, (res, trace) in all_results.items():
        v = res.dropna(subset=["rpm_auto"])["rpm_auto"].values
        if len(v) >= 1:
            data.append(v)
            labels.append(sheet)
            indicators.append(trace.get("indicator", ""))
    if not data:
        return None
    fig, ax = plt.subplots(figsize=(max(6, 0.7 * len(data) + 3), 5))
    bp = ax.boxplot(data, tick_labels=labels, patch_artist=True, widths=0.6)
    for patch, ind in zip(bp["boxes"], indicators):
        patch.set_facecolor("#4C78A8" if ind == "R" else "#F58518")
        patch.set_alpha(0.7)
    ax.set_ylabel("RPM (auto)")
    ax.set_title("Per-segment RPM distribution")
    ax.tick_params(axis="x", rotation=30)
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    if out_path:
        plt.savefig(out_path, dpi=dpi, bbox_inches="tight")
    return fig


def plot_summary_grid(all_results: dict, out_path: str, dpi: int = 85):
    """Grid plot: per-sheet Excel vs Auto RPM."""
    n = len(all_results)
    cols = 2
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(20, 4 * rows))
    axes = np.array(axes).flatten()
    for ax, (sheet, (res, trace)) in zip(axes, all_results.items()):
        valid = res.dropna(subset=["rpm_auto"])
        ax.plot(valid["row"], valid["rpm_xl"], "go-", label="Excel", ms=6)
        ax.plot(valid["row"], valid["rpm_auto"], "r^-", label="Auto", ms=5)
        n_match = int(valid["rot_match"].sum())
        err = float(valid["rpm_err_pct"].abs().mean())
        ax.set_title(
            f"{sheet} ({trace['indicator']}) | "
            f"match={n_match}/{len(valid)} | err={err:.1f}%",
            fontsize=10,
        )
        ax.set_xlabel("row")
        ax.set_ylabel("RPM")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
    for ax in axes[n:]:
        ax.axis("off")
    plt.tight_layout()
    plt.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close()


def plot_agreement(combined_df: pd.DataFrame, out_path: str, dpi: int = 100):
    """Scatter + Bland-Altman + error histogram + per-sheet box.

    Expects columns: rpm_xl, rpm_auto, rpm_err_pct, sheet.
    """
    df = combined_df.dropna(subset=["rpm_auto", "rpm_xl"]).copy()
    df["rpm_diff"] = df["rpm_auto"] - df["rpm_xl"]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    ax = axes[0, 0]
    ax.scatter(df["rpm_xl"], df["rpm_auto"], alpha=0.5, s=20)
    lim_lo = float(df[["rpm_xl", "rpm_auto"]].min().min()) - 5
    lim_hi = float(df[["rpm_xl", "rpm_auto"]].max().max()) + 5
    ax.plot([lim_lo, lim_hi], [lim_lo, lim_hi], "k--", alpha=0.5, label="y=x")
    ax.set_xlabel("Excel RPM (manual)")
    ax.set_ylabel("Auto RPM")
    ax.set_title(f"Manual vs Auto RPM (n={len(df)})")
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_aspect("equal")

    ax = axes[0, 1]
    mean_rpm = (df["rpm_xl"] + df["rpm_auto"]) / 2
    diff = df["rpm_diff"]
    ax.scatter(mean_rpm, diff, alpha=0.5, s=20)
    ax.axhline(diff.mean(), color="r", label=f"bias={diff.mean():.2f}")
    ax.axhline(diff.mean() + 1.96 * diff.std(), color="r", ls="--", alpha=0.5,
               label=f"±1.96σ = ±{1.96 * diff.std():.2f}")
    ax.axhline(diff.mean() - 1.96 * diff.std(), color="r", ls="--", alpha=0.5)
    ax.set_xlabel("Mean RPM ((manual+auto)/2)")
    ax.set_ylabel("Auto - Manual (RPM)")
    ax.set_title("Bland-Altman agreement")
    ax.legend()
    ax.grid(alpha=0.3)

    ax = axes[1, 0]
    ax.hist(df["rpm_err_pct"], bins=40, edgecolor="black")
    ax.axvline(0, color="k", lw=1)
    ax.set_xlabel("Relative error (%)")
    ax.set_ylabel("Row count")
    med = float(df["rpm_err_pct"].abs().median())
    ax.set_title(f"Distribution of relative error (median |err|={med:.2f}%)")
    ax.grid(alpha=0.3)

    ax = axes[1, 1]
    sheets = sorted(df["sheet"].unique())
    ax.boxplot([df[df["sheet"] == s]["rpm_err_pct"] for s in sheets], tick_labels=sheets)
    ax.axhline(0, color="k", lw=1)
    ax.set_ylabel("Relative error (%)")
    ax.set_title("Error distribution per sheet")
    ax.tick_params(axis="x", rotation=45, labelsize=8)
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close()


def plot_roi_overview(sample_bgr, coarse, fine, out_path):
    """Single-frame ROI overview: image + coarse box + fine box + grid."""
    import cv2
    rgb = cv2.cvtColor(sample_bgr, cv2.COLOR_BGR2RGB)
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.imshow(rgb)
    cx, cy, cw, ch = coarse
    ax.add_patch(plt.Rectangle((cx, cy), cw, ch, fill=False, ec="orange", lw=2, label="coarse"))
    if fine:
        fx, fy, fw, fh = fine
        ax.add_patch(plt.Rectangle((fx, fy), fw, fh, fill=False, ec="lime", lw=3, label="fine"))
    ax.set_xticks(np.arange(0, rgb.shape[1] + 1, 200))
    ax.set_yticks(np.arange(0, rgb.shape[0] + 1, 200))
    ax.grid(color="cyan", alpha=0.3, lw=0.4)
    ax.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=85, bbox_inches="tight")
    plt.close()
