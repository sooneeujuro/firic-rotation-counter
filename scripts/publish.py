"""Semi-automated publishing helper.

Fills in CITATION.cff from user info, initializes git, creates a public
GitHub repo via `gh`, pushes the initial commit, and creates a v0.1.0
release. Stops there — the only remaining manual step is toggling the
repo ON in Zenodo's GitHub settings (one-time, 30 seconds), then making
the release will trigger Zenodo's webhook to mint a DOI.

After the DOI is issued, run `update_doi.py` with the DOI to finalize.

Prerequisites:
  - `gh` CLI installed and authenticated (`gh auth login` once)
  - `git` installed
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(cmd, **kw):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, text=True, capture_output=True, **kw)
    if r.stdout:
        print(r.stdout, end="")
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        sys.exit(r.returncode)
    return r.stdout.strip()


def fill_citation(path, family, given, email, affiliation, orcid, gh_user, repo_name, today):
    with open(path, "r", encoding="utf-8") as f:
        s = f.read()
    s = re.sub(r'family-names: "YOUR_FAMILY_NAME".*?TODO.*', f'family-names: "{family}"', s)
    s = re.sub(r'given-names: "YOUR_GIVEN_NAME".*?TODO.*', f'given-names: "{given}"', s)
    s = re.sub(r'affiliation: "YOUR_AFFILIATION".*?TODO.*', f'affiliation: "{affiliation}"', s)
    url = f"https://github.com/{gh_user}/{repo_name}"
    s = re.sub(r'repository-code: "https://github.com/USERNAME/firic-rotation-counter".*',
               f'repository-code: "{url}"', s)
    s = re.sub(r'url: "https://github.com/USERNAME/firic-rotation-counter".*',
               f'url: "{url}"', s)
    s = re.sub(r'date-released: ".*?".*', f'date-released: "{today}"', s)
    if orcid:
        orcid_url = orcid if orcid.startswith("http") else f"https://orcid.org/{orcid}"
        s = re.sub(r'    # orcid: ".*"\s*# TODO.*', f'    orcid: "{orcid_url}"', s)
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)
    print(f"updated {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True, help="Last name, e.g. Kim")
    ap.add_argument("--given", required=True, help="First name, e.g. Sooneeu")
    ap.add_argument("--email", default="sooneeujuro@gmail.com")
    ap.add_argument("--affiliation", required=True, help='Institution, e.g. "Korea Institute of ..."')
    ap.add_argument("--orcid", default="", help="ORCID id (e.g. 0000-0000-0000-0000) or full URL, optional")
    ap.add_argument("--gh-user", required=True, help="Your GitHub username")
    ap.add_argument("--repo", default="firic-rotation-counter", help="Repository name to create")
    ap.add_argument("--public", action="store_true", default=True)
    args = ap.parse_args()

    today = date.today().isoformat()

    cff = os.path.join(ROOT, "CITATION.cff")
    fill_citation(cff, args.family, args.given, args.email, args.affiliation,
                  args.orcid, args.gh_user, args.repo, today)

    os.chdir(ROOT)
    if not os.path.exists(".git"):
        run("git init -b main")
    run('git add -A')
    has_change = subprocess.run("git diff --cached --quiet", shell=True).returncode != 0
    if has_change:
        run('git commit -m "Initial release: firic-rotation-counter v0.1.0"')

    remote_exists = subprocess.run("git remote get-url origin",
                                   shell=True, capture_output=True).returncode == 0
    if not remote_exists:
        vis = "--public" if args.public else "--private"
        run(f"gh repo create {args.gh_user}/{args.repo} {vis} --source=. --remote=origin --push")
    else:
        run("git push -u origin main")

    notes = (
        "First public release.\\n\\n"
        "- Two-stage ROI pipeline (manual coarse + automatic flicker-based fine ROI)\\n"
        "- HSV peak detection with smoke-aware interpolation\\n"
        "- Validated on 227 manually-counted rows across 10 ROV dive videos\\n"
        "  (96.5% rotation match, 0.00% median RPM error)"
    )
    existing = subprocess.run("gh release view v0.1.0", shell=True, capture_output=True).returncode == 0
    if not existing:
        run(f'gh release create v0.1.0 --title "v0.1.0 - Initial release" --notes "{notes}"')
    else:
        print("release v0.1.0 already exists, skipping")

    print()
    print("=" * 70)
    print("Done. Manual steps remaining:")
    print("  1. Go to https://zenodo.org and log in with GitHub.")
    print(f"  2. Settings -> GitHub -> toggle '{args.gh_user}/{args.repo}' to ON.")
    print("  3. Go back to GitHub releases page and click 'Re-run' on the")
    print("     v0.1.0 release (or create v0.1.1) to trigger Zenodo.")
    print("     (If you toggled ON BEFORE creating the release, no re-trigger needed.)")
    print("  4. Wait ~1 minute, then check https://zenodo.org/account/settings/github/")
    print("     for the issued DOI.")
    print()
    print("Once you have the DOI:")
    print(f"  python scripts/update_doi.py --doi 10.5281/zenodo.XXXXXXX --badge-id NNNNNNNNN")
    print("=" * 70)


if __name__ == "__main__":
    main()
