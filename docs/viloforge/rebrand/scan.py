#!/usr/bin/env python3
"""Run the Tier-4 exclusion allowlist against the live repo and report coverage.

E2E self-check for ``exclusions.py``: walks every git-tracked text file, counts
how much of the do-not-touch surface each ADR-0003 D4 pattern actually catches,
and surfaces the "trap" lines where a rebrandable ``hermes`` brand token shares a
line with a protected token. Use this to eyeball that the allowlist matches the
known blast-radius (e.g. hermes-[0-9] ≈ 49 files, nousresearch ≈ 421 files,
NOUS_* ≈ 32 vars) before trusting a codemod that depends on it.

    python docs/viloforge/rebrand/scan.py            # coverage table
    python docs/viloforge/rebrand/scan.py --traps    # also list trap lines
    python docs/viloforge/rebrand/scan.py --tier3     # include deferred skeleton

Read-only. No edits. Exits 0 always (it is a report, not a gate).
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exclusions as ex  # noqa: E402

# A rebrandable brand token (the kind a Tier-1/2 codemod targets) — used only to
# find "trap" lines where brand + protected token coexist. Deliberately broad.
_BRAND = re.compile(r"hermes", re.IGNORECASE)


def _repo_root() -> str:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    )
    return out.stdout.strip()


def _tracked_files(root: str) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True
    )
    return [p for p in out.stdout.splitlines() if p]


def _read(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except (UnicodeDecodeError, OSError):
        return None  # binary / unreadable — skip


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--traps", action="store_true",
                    help="list lines where a brand token shares a line with a protected token")
    ap.add_argument("--tier3", action="store_true",
                    help="include the deferred hermes_cli / HERMES_* skeleton")
    args = ap.parse_args()

    root = _repo_root()
    files = _tracked_files(root)

    patterns = ex.all_patterns(include_tier3=args.tier3)
    pat_files: dict[str, set[str]] = {p.name: set() for p in patterns}
    pat_lines: dict[str, int] = {p.name: 0 for p in patterns}
    distinct_nous_vars: set[str] = set()
    distinct_hermes_vars: set[str] = set()

    path_excluded_files: list[tuple[str, str]] = []
    trap_hits: list[tuple[str, int, str]] = []

    nous_var_re = re.compile(r"NOUS_[A-Z0-9_]+")
    hermes_var_re = re.compile(r"HERMES_[A-Z0-9_]+")

    for rel in files:
        excluded, reason = ex.path_excluded(rel)
        if excluded:
            path_excluded_files.append((rel, reason))

        text = _read(os.path.join(root, rel))
        if text is None:
            continue

        for var_m in nous_var_re.finditer(text):
            distinct_nous_vars.add(var_m.group(0))
        for var_m in hermes_var_re.finditer(text):
            distinct_hermes_vars.add(var_m.group(0))

        for ln_no, line in enumerate(text.splitlines(), 1):
            spans = ex.protected_spans(line, include_tier3=args.tier3)
            if not spans:
                continue
            names_on_line = {n for _, _, n in spans}
            for n in names_on_line:
                pat_files[n].add(rel)
            for _, _, n in spans:
                pat_lines[n] += 1

            if args.traps:
                # A trap: line has a rebrandable brand token OUTSIDE every
                # protected span (a span-aware codemod would rewrite it).
                protected_ranges = [(s, e) for s, e, _ in spans]
                for bm in _BRAND.finditer(line):
                    inside = any(s <= bm.start() < e for s, e in protected_ranges)
                    if not inside:
                        trap_hits.append((rel, ln_no, line.strip()[:160]))
                        break

    print("=" * 72)
    print("Tier-4 exclusion allowlist — live-repo coverage (ADR-0003 D4)")
    print(f"repo: {root}")
    print(f"tracked files scanned: {len(files)}")
    print("=" * 72)
    print(f"{'pattern':<28}{'category':<12}{'files':>7}{'lines':>8}")
    print("-" * 72)
    for p in patterns:
        print(f"{p.name:<28}{p.d4_category:<12}{len(pat_files[p.name]):>7}{pat_lines[p.name]:>8}")
    print("-" * 72)
    print(f"distinct NOUS_* vars (do-not-touch): {len(distinct_nous_vars)}")
    print(f"distinct HERMES_* vars (Tier-3 deferred): {len(distinct_hermes_vars)}")
    print(f"path-excluded files (whole-file do-not-touch): {len(path_excluded_files)}")
    for rel, reason in sorted(path_excluded_files):
        print(f"    {rel}  <- {reason}")

    if args.traps:
        print("=" * 72)
        print(f"TRAP lines (brand token outside every protected span): {len(trap_hits)}")
        print("These are where a span-aware codemod could still rewrite a brand")
        print("token that should be reviewed by a human (e.g. *.nousresearch.com).")
        print("-" * 72)
        for rel, ln_no, snippet in trap_hits[:60]:
            print(f"{rel}:{ln_no}: {snippet}")
        if len(trap_hits) > 60:
            print(f"... and {len(trap_hits) - 60} more")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
