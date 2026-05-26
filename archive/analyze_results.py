"""
수동 vs 자동 결과 정량 분석.
- 시트별 통계 (rotation 일치율, RPM 차이 분포, 시간 차이)
- 전체 분포 (평균, median, 95%ile, max)
- Outlier row 식별
- Bland-Altman 스타일 agreement plot
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import glob

OUT_DIR = r"C:\Users\USER\Firic_regular\samples"

csv_files = sorted(glob.glob(os.path.join(OUT_DIR, "compare_*.csv")))
all_rows = []
for csv in csv_files:
    sheet = os.path.basename(csv).replace("compare_", "").replace(".csv", "")
    df = pd.read_csv(csv)
    df["sheet"] = sheet
    all_rows.append(df)
df = pd.concat(all_rows, ignore_index=True)
df = df.dropna(subset=["rpm_auto", "rpm_xl"]).reset_index(drop=True)

df["rpm_diff"] = df["rpm_auto"] - df["rpm_xl"]
df["rpm_err_abs"] = df["rpm_diff"].abs()
df["rpm_err_pct"] = df["rpm_diff"] / df["rpm_xl"] * 100
df["rot_diff"] = df["rot_auto"] - df["rot_xl"]
df["rot_match"] = (df["rot_auto"].round() == df["rot_xl"])

print("=" * 80)
print("전체 통계 (n={})".format(len(df)))
print("=" * 80)
print(f"{'Metric':<35} {'Value':>15}")
print("-" * 50)
print(f"{'Rotation 정수 일치율':<35} {df['rot_match'].sum()}/{len(df)} ({df['rot_match'].mean()*100:.1f}%)")
print(f"{'RPM 평균 절대오차':<35} {df['rpm_err_abs'].mean():>12.2f} RPM")
print(f"{'RPM median 절대오차':<35} {df['rpm_err_abs'].median():>12.2f} RPM")
print(f"{'RPM 95%ile 절대오차':<35} {df['rpm_err_abs'].quantile(0.95):>12.2f} RPM")
print(f"{'RPM max 절대오차':<35} {df['rpm_err_abs'].max():>12.2f} RPM")
print(f"{'RPM 평균 상대오차':<35} {df['rpm_err_pct'].abs().mean():>12.2f} %")
print(f"{'RPM median 상대오차':<35} {df['rpm_err_pct'].abs().median():>12.2f} %")
print(f"{'RPM 95%ile 상대오차':<35} {df['rpm_err_pct'].abs().quantile(0.95):>12.2f} %")
print(f"{'Bias (signed mean diff)':<35} {df['rpm_diff'].mean():>+12.2f} RPM")

print()
print("=" * 80)
print("시트별 통계")
print("=" * 80)
by_sheet = df.groupby("sheet").agg(
    n=("row", "count"),
    rot_match_rate=("rot_match", lambda x: f"{x.sum()}/{len(x)} ({x.mean()*100:.0f}%)"),
    mean_abs_err=("rpm_err_abs", "mean"),
    median_abs_err=("rpm_err_abs", "median"),
    max_abs_err=("rpm_err_abs", "max"),
    mean_pct_err=("rpm_err_pct", lambda x: x.abs().mean()),
    bias=("rpm_diff", "mean"),
).round(2)
print(by_sheet.to_string())

print()
print("=" * 80)
print("Outlier rows (|RPM 차이| > 10)")
print("=" * 80)
outliers = df[df["rpm_err_abs"] > 10].sort_values("rpm_err_abs", ascending=False)
if len(outliers) > 0:
    cols = ["sheet", "row", "init", "final", "rot_xl", "rot_auto", "rpm_xl", "rpm_auto", "rpm_diff", "src"]
    print(outliers[cols].to_string(index=False))
else:
    print("없음")

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

ax = axes[0, 0]
ax.scatter(df["rpm_xl"], df["rpm_auto"], alpha=0.5, s=20)
lim = [df[["rpm_xl", "rpm_auto"]].min().min() - 5, df[["rpm_xl", "rpm_auto"]].max().max() + 5]
ax.plot(lim, lim, "k--", alpha=0.5, label="y=x")
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
ax.axhline(diff.mean() + 1.96 * diff.std(), color="r", ls="--", alpha=0.5, label=f"±1.96σ = ±{1.96*diff.std():.2f}")
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
ax.set_title(f"Distribution of relative error (median |err|={df['rpm_err_pct'].abs().median():.2f}%)")
ax.grid(alpha=0.3)

ax = axes[1, 1]
sheets = list(by_sheet.index)
ax.boxplot([df[df["sheet"] == s]["rpm_err_pct"] for s in sheets], labels=sheets)
ax.axhline(0, color="k", lw=1)
ax.set_ylabel("Relative error (%)")
ax.set_title("Error distribution per sheet")
ax.tick_params(axis="x", rotation=45, labelsize=8)
ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "agreement_analysis.png"), dpi=100, bbox_inches="tight")
print(f"\nsaved agreement_analysis.png")
