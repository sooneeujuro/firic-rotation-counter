"""Finalize publishing: write Zenodo DOI into CITATION.cff and README, then push.

After scripts/publish.py and the Zenodo webhook, Zenodo gives you:
  - DOI like  10.5281/zenodo.12345678
  - Badge ID (the numeric part of the badge SVG URL)

You can find both on the Zenodo deposit page:
  - DOI is shown prominently
  - Badge URL on the right side: https://zenodo.org/badge/<BADGE_ID>.svg
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(cmd):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if r.stdout:
        print(r.stdout, end="")
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        sys.exit(r.returncode)


def patch_file(path, replacements):
    with open(path, "r", encoding="utf-8") as f:
        s = f.read()
    for pat, repl in replacements:
        s = re.sub(pat, repl, s)
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)
    print(f"updated {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doi", required=True, help="Zenodo DOI, e.g. 10.5281/zenodo.12345678")
    ap.add_argument("--badge-id", required=True, help="Zenodo badge ID (numeric)")
    ap.add_argument("--no-push", action="store_true", help="Don't git push after committing")
    args = ap.parse_args()

    doi = args.doi.replace("https://doi.org/", "")
    doi_num = doi.split("/")[-1].replace("zenodo.", "")

    patch_file(
        os.path.join(ROOT, "CITATION.cff"),
        [
            (r'# doi: "10\.5281/zenodo\.XXXXXXX".*',
             f'doi: "{doi}"'),
        ],
    )

    patch_file(
        os.path.join(ROOT, "README.md"),
        [
            (r"BADGE_ID", args.badge_id),
            (r"DOI_HERE", doi_num),
        ],
    )

    os.chdir(ROOT)
    run('git add -A')
    run(f'git commit -m "Add Zenodo DOI {doi}"')
    if not args.no_push:
        run("git push")

    print()
    print(f"Done. DOI {doi} embedded in CITATION.cff and README.md.")
    print(f"Department metadata snippet:")
    print(f"  https://doi.org/{doi}")


if __name__ == "__main__":
    main()
