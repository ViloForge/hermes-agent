"""Diff-scoped do-not-touch gate for the ViloForge rebrand (ADR-0004 L2).

Fails if a changeset **corrupts** an inviolable token — i.e. an added line
contains a do-not-touch / skeleton token in a *rebranded* form. These corruption
signatures (`x-viloforge-`, `viloforge-3`, `viloforge_cli`, `Nous ViloForge`, …)
are what the brand codemod produces when it bleeds into a protected span; they do
not occur in legitimate code, so the gate has ~zero false positives and is safe to
run as a hard, merge-blocking CI check.

Why corruption signatures and not "added line is protected" (the predicate the
first ADR-0004 draft named): a *correctly* rebranded line — e.g.
``ViloForge Agent uses hermes_cli`` — still contains the **preserved** protected
token ``hermes_cli``. Flagging it would false-fail correct work and the gate would
get disabled. We instead detect the *broken* form, which only a corrupting codemod
can produce. The signatures are derived from the guard's patterns
(``exclusions.all_patterns``) + the brand mapping, so the boundary stays one source
of truth; ``test_diff_gate.py`` pins that every brand-bearing guard pattern has a
matching signature.

Diff-scoped (a property of the changeset, recomputed each run) — NOT a committed
tree-wide token-count baseline (ADR-0004 D2), so ``--merge`` upstream syncs do not
trip it.

Usage::

    # local pre-PR (diff against the merge base with origin/main):
    python docs/viloforge/rebrand/diff_gate.py
    python docs/viloforge/rebrand/diff_gate.py --base origin/main --head HEAD
    # from a pre-computed diff (CI, tests):
    git diff origin/main...HEAD | python docs/viloforge/rebrand/diff_gate.py --stdin

Escape hatch: a deliberately-corrupted-looking line (extremely rare) can be
suppressed by adding the marker ``rebrand-gate: ok`` to that line — visible in the
diff and reviewable, so it cannot silently weaken the gate.

Self-exemption: the gate's own machinery (``docs/viloforge/rebrand/``), its CI
workflow, and the governance docs that document the signatures (ADR-0004, rebrand
plans) legitimately contain signature strings as fixtures/examples, so the gate
skips them (``_self_exempt``) — the standard linter pattern of not flagging your
own test fixtures.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exclusions as _ex  # noqa: E402

SUPPRESS_MARKER = "rebrand-gate: ok"

# The gate's own machinery + the governance docs that DESCRIBE it legitimately
# contain corruption-signature strings (fixtures, examples, comments). Scanning
# them would flag the very examples that document what the gate catches, so the
# gate skips them — standard linter self-exemption. (`str.startswith` takes a
# tuple; the ADR-0004 file is matched by substring since its full name is long.)
_SELF_EXEMPT_PREFIXES = (
    "docs/viloforge/rebrand/",            # guard / transform / gate + tests + README
    "docs/viloforge/plans/",             # rebrand plans cite the signatures in prose
    ".github/workflows/rebrand-guard.yml",  # the gate's own CI workflow
)


def _self_exempt(relpath: str) -> bool:
    # NB: strip a leading "./" only — lstrip("./") would also eat the leading dot
    # of dotdirs like ".github", breaking the prefix match.
    rp = relpath.replace("\\", "/")
    if rp.startswith("./"):
        rp = rp[2:]
    return rp.startswith(_SELF_EXEMPT_PREFIXES) or "ADR-0004" in rp


@dataclass(frozen=True)
class CorruptionSignature:
    name: str
    regex: "re.Pattern[str]"
    guards: str  # the exclusions.py pattern name this protects
    note: str


# Each signature = "what a protected token becomes if the Hermes→ViloForge codemod
# corrupts it." Only patterns whose protected token CONTAINS a rebrandable brand
# token (capital `Hermes`, or the all-caps `NOUS HERMES` banner) are producible;
# pure-`nous` tokens (nousresearch, NOUS_, x-nous-, psyche, atropos) cannot be
# corrupted by a Hermes→ViloForge map and so have no signature.
CORRUPTION_SIGNATURES: List[CorruptionSignature] = [
    CorruptionSignature(
        "x-viloforge-header", re.compile(r"x-viloforge-", re.IGNORECASE),
        "x-hermes-header",
        "X-Hermes-* wire-contract header rebranded (the Tier-1b near-miss).",
    ),
    CorruptionSignature(
        "viloforge-model-id", re.compile(r"viloforge-[0-9]", re.IGNORECASE),
        "hermes-model-id",
        "Nous Hermes model ID (hermes-3, hermes-4, …) rebranded.",
    ),
    CorruptionSignature(
        "nous-viloforge", re.compile(r"nous[-_/]viloforge", re.IGNORECASE),
        "nous-hermes",
        "nous-hermes / nousresearch/hermes-* model family rebranded.",
    ),
    CorruptionSignature(
        "nous-viloforge-spaced", re.compile(r"Nous\s+ViloForge"),
        "nous-hermes-spaced",
        "'Nous Hermes' model-family prose rebranded.",
    ),
    CorruptionSignature(
        "viloforge-model-spaced", re.compile(r"ViloForge\s+[0-9]"),
        "hermes-model-spaced",
        "'Hermes 3'/'Hermes 4' model-family prose rebranded.",
    ),
    CorruptionSignature(
        "trap-host-viloforge",
        re.compile(r"viloforge--?agent\.nousresearch", re.IGNORECASE),
        "trap-host-hermes-agent",
        "hermes-agent.nousresearch.com upstream-infra host rebranded.",
    ),
    CorruptionSignature(
        "viloforge_cli", re.compile(r"viloforge_cli", re.IGNORECASE),
        "hermes_cli-namespace",
        "hermes_cli internal namespace (Tier-3 deferred) rebranded.",
    ),
    CorruptionSignature(
        "viloforge-env-prefix", re.compile(r"VILOFORGE_[A-Z]"),
        "HERMES-env-prefix",
        "HERMES_* env prefix (Tier-3 deferred, kept + aliased) rebranded.",
    ),
]


@dataclass(frozen=True)
class Violation:
    path: str
    line_no: int  # new-file line number of the offending added line
    signature: str
    guards: str
    text: str


def _added_lines(diff_text: str):
    """Yield (path, new_line_no, content) for every added (+) line in a unified
    diff. Skips +++ headers; tracks new-file line numbers from @@ hunks."""
    path: Optional[str] = None
    new_no = 0
    for raw in diff_text.splitlines():
        if raw.startswith("+++ "):
            p = raw[4:].strip()
            # strip the b/ prefix git adds; "/dev/null" for deletions
            path = None if p == "/dev/null" else re.sub(r"^b/", "", p)
            continue
        if raw.startswith("--- "):
            continue
        if raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            new_no = int(m.group(1)) if m else 0
            continue
        if raw.startswith("+"):
            yield path, new_no, raw[1:]
            new_no += 1
        elif raw.startswith("-"):
            continue  # removed line: does not advance the new-file counter
        else:
            new_no += 1  # context line


def scan_diff(diff_text: str) -> List[Violation]:
    """Pure core: return corruption violations in a unified diff. Skips files the
    guard excludes wholesale and lines carrying the suppression marker."""
    out: List[Violation] = []
    for path, line_no, content in _added_lines(diff_text):
        if path is None:
            continue
        excluded, _ = _ex.path_excluded(path)
        if excluded:
            continue
        if _self_exempt(path):
            continue
        if SUPPRESS_MARKER in content:
            continue
        for sig in CORRUPTION_SIGNATURES:
            if sig.regex.search(content):
                out.append(Violation(path, line_no, sig.name, sig.guards, content.rstrip()))
    return out


def _git_diff(base: str, head: str) -> str:
    # three-dot: changes on `head` since its merge-base with `base`.
    return subprocess.run(
        ["git", "diff", "--no-color", "--unified=3", f"{base}...{head}"],
        capture_output=True, text=True, check=True,
    ).stdout


def _format(violations: List[Violation]) -> str:
    lines = ["✘ rebrand do-not-touch gate FAILED — corrupted protected token(s):", ""]
    for v in violations:
        lines.append(f"  {v.path}:{v.line_no}  [{v.signature} → guards {v.guards}]")
        lines.append(f"      + {v.text}")
    lines += [
        "",
        "A protected/skeleton token (ADR-0003 D4 / Tier-3) was rewritten by the brand",
        "codemod. Fix the codemod's protected-span handling (docs/viloforge/rebrand/),",
        f"or, if genuinely intentional, add the marker '{SUPPRESS_MARKER}' to the line.",
    ]
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Diff-scoped rebrand do-not-touch gate (ADR-0004 L2).")
    ap.add_argument("--base", default="origin/main", help="base ref (default: origin/main)")
    ap.add_argument("--head", default="HEAD", help="head ref (default: HEAD)")
    ap.add_argument("--stdin", action="store_true", help="read a unified diff from stdin instead of running git")
    args = ap.parse_args(argv)

    diff = sys.stdin.read() if args.stdin else _git_diff(args.base, args.head)
    violations = scan_diff(diff)
    if violations:
        print(_format(violations), file=sys.stderr)
        return 1
    print("✓ rebrand do-not-touch gate passed (no protected token corrupted).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
