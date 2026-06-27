"""Global display-brand completeness sweep (ADR-0004 L3, extended repo-wide).

The do-not-touch gate (`diff_gate.py`) stops us corrupting what we *shouldn't*
rebrand. This stops us *missing* what we should. It is the safeguard the Tier-1
misses needed: it scans the **whole repo** (every surface) instead of a hand-listed
directory set, so an unscoped surface (the `ui-tui/` banner) or a shadowing backend
copy (`hermes_cli/web_server.py` theme labels) shows up as a residual.

A **residual** is a line the tested transform (`rebrand_apply.rebrand_text`) would
*still* change — i.e. a display-brand token (`Hermes Agent`, `HERMES-AGENT`,
standalone `Hermes`, the `NOUS HERMES` banner, …) that has not been rebranded. Because
the residual oracle IS the transform, the do-not-touch boundary and the Tier-3
skeleton are already excluded (the transform skips protected spans). On top of that we
subtract:

* the **intentional-keep set** — fork notices ("a ViloForge fork of Hermes Agent") and
  attribution, which deliberately keep the upstream name (see `INTENTIONAL_KEEP`);
* **self-exempt paths** — the rebrand tooling and the governance docs/ADRs that discuss
  these tokens as *examples* (see `_self_exempt`).

Pair this token sweep with the knowledge-graph *surface* map — neither substitutes for
the other (`docs/viloforge/knowledge-graph-vs-grep.md`).

Usage:
    python docs/viloforge/rebrand/completeness.py              # per-surface residual report
    python docs/viloforge/rebrand/completeness.py --list       # full file:line work-list
    python docs/viloforge/rebrand/completeness.py --surface ui-tui   # restrict to one surface
    python docs/viloforge/rebrand/completeness.py --surface cli --max 0   # HARD gate: fail if any
                                                                          # residual remains in a
                                                                          # surface you've declared done

Default exit is 0 (report). `--max N` (optionally with `--surface`) exits non-zero when
the residual count exceeds N — that is how a surface becomes a hard gate once its tier
lands. Today the repo still has residuals (Tier-1d/2 unfinished), so the bare sweep is a
work-list generator, not yet a zero-gate.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections import defaultdict
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exclusions as _ex  # noqa: E402
import rebrand_apply as _ra  # noqa: E402

# Lines the transform *would* change but that deliberately keep the upstream name.
INTENTIONAL_KEEP: List["re.Pattern[str]"] = [
    re.compile(r"\bfork of\b", re.IGNORECASE),          # "a ViloForge fork of Hermes Agent"
    re.compile(r"\bforked from\b", re.IGNORECASE),
    re.compile(r"Built by Nous", re.IGNORECASE),        # attribution footer
    re.compile(r"NousResearch/hermes-agent", re.IGNORECASE),  # attribution links to the upstream repo
    re.compile(r"Copyright \(c\)", re.IGNORECASE),      # copyright notices = attribution; never brand-rebrand (e.g. vendored third-party plugin LICENSEs)
    re.compile(r"completeness-gate:\s*keep"),           # explicit in-line opt-out marker
]

# Directories/files that *talk about* the brand tokens (tooling + governance) and so
# must not be swept as product surface.
_SELF_EXEMPT_PREFIXES = (
    "docs/viloforge/",      # rebrand tooling, plans, governance notes
    "docs/adr/",            # ADRs cite "Hermes Agent" / "HERMES-AGENT"
    ".understand-anything/",  # generated knowledge-graph artifact (regenerated, not source)
)
_SELF_EXEMPT_FILES = ("AGENTS.md", "CLAUDE.md")


def _self_exempt(relpath: str) -> bool:
    rp = relpath.replace("\\", "/")
    if rp.startswith("./"):
        rp = rp[2:]
    return rp.startswith(_SELF_EXEMPT_PREFIXES) or rp in _SELF_EXEMPT_FILES


# Surface attribution — the five display surfaces + structural buckets. Order matters
# (first match wins).
_SURFACES: List[Tuple[str, "re.Pattern[str]"]] = [
    ("TUI", re.compile(r"^ui-tui/")),
    ("Web", re.compile(r"^web/")),
    ("Docs", re.compile(r"^website/")),
    ("Desktop", re.compile(r"^apps/")),
    ("Gateway", re.compile(r"^gateway/")),
    ("CLI", re.compile(r"^(cli\.py|hermes_cli/)")),
    ("Skills", re.compile(r"^(skills/|optional-skills/)")),
    ("Plugins", re.compile(r"^plugins/")),
    ("Agent core", re.compile(r"^(agent/|run_agent\.py|model_tools\.py|toolsets\.py)")),
    ("Tests", re.compile(r"^tests/")),
]


def surface_of(relpath: str) -> str:
    for name, rx in _SURFACES:
        if rx.search(relpath):
            return name
    return "Other"


def _git_tracked_files() -> List[str]:
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout
    return [l for l in out.splitlines() if l]


def residual_lines(text: str) -> List[Tuple[int, str]]:
    """Return (line_no, original_line) for lines the transform would change and that
    are not in the intentional-keep set. Empty when the file is fully rebranded."""
    new = _ra.rebrand_text(text)
    if new == text:
        return []
    out: List[Tuple[int, str]] = []
    # rebrand_text does in-line substring replacement → line count is preserved.
    for i, (a, b) in enumerate(zip(text.splitlines(), new.splitlines()), 1):
        if a != b and not any(k.search(a) for k in INTENTIONAL_KEEP):
            out.append((i, a.strip()))
    return out


def sweep(surface_filter: str | None = None) -> Dict[str, List[Tuple[str, int, str]]]:
    """Map surface → list of (path, line_no, line). Skips do-not-touch paths,
    self-exempt paths, binaries, and files with no brand token at all (fast path)."""
    by_surface: Dict[str, List[Tuple[str, int, str]]] = defaultdict(list)
    for rel in _git_tracked_files():
        excluded, _ = _ex.path_excluded(rel)
        if excluded or _self_exempt(rel):
            continue
        surf = surface_of(rel)
        if surface_filter and surf.lower() != surface_filter.lower():
            continue
        try:
            with open(rel, "r", encoding="utf-8") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError):
            continue  # binary / unreadable
        if "Hermes" not in text and "HERMES" not in text:
            continue  # fast prune: no brand token possible
        for line_no, line in residual_lines(text):
            by_surface[surf].append((rel, line_no, line))
    return by_surface


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Repo-wide display-brand completeness sweep (ADR-0004 L3).")
    ap.add_argument("--list", action="store_true", help="print the full file:line work-list")
    ap.add_argument("--surface", help="restrict to one surface (TUI/Web/Docs/Desktop/CLI/...)")
    ap.add_argument("--max", type=int, default=None, help="exit non-zero if residual count exceeds this")
    args = ap.parse_args(argv)

    by_surface = sweep(args.surface)
    total = sum(len(v) for v in by_surface.values())
    files = {p for v in by_surface.values() for (p, _, _) in v}

    print("Residual display-brand tokens (lines the rebrand transform would still change):\n")
    if not by_surface:
        print("  ✓ none — every swept surface is fully rebranded.")
    else:
        for surf in sorted(by_surface, key=lambda s: -len(by_surface[s])):
            hits = by_surface[surf]
            nfiles = len({p for p, _, _ in hits})
            print(f"  {surf:11s} {len(hits):5d} lines  ·  {nfiles} files")
            if args.list:
                for p, ln, line in sorted(hits):
                    snip = (line[:100] + "…") if len(line) > 100 else line
                    print(f"      {p}:{ln}: {snip}")
            else:
                for p, ln, _ in sorted(hits)[:3]:
                    print(f"      e.g. {p}:{ln}")
        print(f"\n  total: {total} residual lines across {len(files)} files"
              + (f" (surface={args.surface})" if args.surface else ""))

    print("\n  (do-not-touch + Tier-3 skeleton are excluded by the transform; fork notices /"
          "\n   attribution are excluded by the intentional-keep set. Add `completeness-gate: keep`"
          "\n   to a line to keep it deliberately.)")

    if args.max is not None and total > args.max:
        print(f"\n✘ completeness gate: {total} residual lines > --max {args.max}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
