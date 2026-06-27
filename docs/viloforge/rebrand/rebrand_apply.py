"""Guard-aware brand transform for the ViloForge rebrand (ADR-0004 L1).

The single, tested implementation of the "Hermes → ViloForge" *display* codemod.
It replaces brand tokens **only outside** the do-not-touch spans flagged by
``exclusions.py`` — so the transform and the guard share one source of truth
(ADR-0004 D3). Promoted out of throwaway ``scratchpad/`` apply scripts that
re-derived these regexes every slice (and once nearly corrupted ``X-Hermes-*``).

Pure stdlib so it runs in any environment, independent of the test tree / CI.

Design:

* **Case-sensitive, word-boundary** brand tokens (``\\bHermes Agent\\b`` etc.).
  Word boundaries protect identifiers (``HermesCLI``, ``updateHermes``) and the
  lowercase package token (``hermes-agent`` — a Tier-2 target, not display).
* **Longest match first** so ``Hermes Agent`` → ``ViloForge Agent`` wins over the
  bare ``Hermes`` → ``ViloForge`` rule.
* **Skip any match overlapping a protected span** (``include_tier3=True`` by
  default — Tier-1/2 codemods run during the ADR-0002 leash, so the deferred
  ``hermes_cli`` / ``HERMES_*`` / ``X-Hermes-*`` skeleton must be skipped too).

This module does *content* transformation only. Whole-file path exclusion
(``exclusions.path_excluded``) is the caller's responsibility — skip those files
before reading them.
"""

from __future__ import annotations

import os
import re
import sys
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exclusions as _ex  # noqa: E402

# Operator-decided brand mapping (ADR-0003 D1 + the plan's Tier-1 brand mapping).
# Order matters only for readability; matching is longest-first via the regex
# alternation built below.
DEFAULT_MAPPING: Dict[str, str] = {
    "Hermes Agent": "ViloForge Agent",
    "Hermes Desktop": "ViloForge Desktop",
    "NOUS HERMES": "VILOFORGE",  # the cli.py framework banner
    "Hermes": "ViloForge",
}


def _build_regex(mapping: Dict[str, str]) -> "re.Pattern[str]":
    # Longest first so multi-word tokens win over the bare "Hermes". Each token
    # is wrapped in ASCII-only boundaries; case-sensitive (no IGNORECASE) so the
    # lowercase package token `hermes-agent` and model IDs are never matched here.
    #
    # We use explicit ASCII lookarounds — (?<![A-Za-z0-9_]) / (?![A-Za-z0-9_]) —
    # NOT Python's `\b`. `\b` is Unicode-aware: a CJK/accented letter counts as a
    # word char, so `\bHermes\b` does NOT match "Hermes" when it is glued directly
    # to a non-ASCII letter (e.g. the Korean "Hermes가" or Chinese "Hermes를").
    # That silently skipped display residuals in CJK i18n strings (caught only by a
    # live preview, since `completeness` reuses this same regex). The ASCII
    # lookarounds still protect identifiers (`HermesAgent`, `updateHermes`,
    # `Hermes_x`) exactly as `\b` did, while treating the boundary with any
    # non-ASCII-word character as rebrandable.
    keys = sorted(mapping, key=len, reverse=True)
    alt = "|".join(re.escape(k) for k in keys)
    return re.compile(r"(?<![A-Za-z0-9_])(?:" + alt + r")(?![A-Za-z0-9_])")


def _overlaps(ms: int, me: int, spans: List[Tuple[int, int, str]]) -> bool:
    for ps, pe, _ in spans:
        if ms < pe and ps < me:
            return True
    return False


def rebrand_text(
    text: str,
    mapping: Dict[str, str] | None = None,
    include_tier3: bool = True,
) -> str:
    """Return `text` with brand tokens replaced outside protected spans.

    A brand match that overlaps any ``exclusions.protected_spans`` region is left
    untouched (conservative: under-rebrand is caught by the L3 completeness check;
    corrupting a protected token is not recoverable).
    """
    mapping = DEFAULT_MAPPING if mapping is None else mapping
    spans = _ex.protected_spans(text, include_tier3=include_tier3)
    pattern = _build_regex(mapping)

    out: List[str] = []
    last = 0
    for m in pattern.finditer(text):
        if _overlaps(m.start(), m.end(), spans):
            continue
        out.append(text[last:m.start()])
        out.append(mapping[m.group(0)])
        last = m.end()
    out.append(text[last:])
    return "".join(out)


def rebrand_file_preview(path: str, **kw) -> Tuple[str, str]:
    """Read `path`, return (original, rebranded). Does not write. Honors the
    whole-file path-exclusion guard (returns the file unchanged if excluded)."""
    excluded, _reason = _ex.path_excluded(path)
    with open(path, "r", encoding="utf-8") as fh:
        original = fh.read()
    if excluded:
        return original, original
    return original, rebrand_text(original, **kw)


if __name__ == "__main__":
    # Tiny CLI: `python rebrand_apply.py <file>` prints a unified diff preview.
    import difflib

    for p in sys.argv[1:]:
        orig, new = rebrand_file_preview(p)
        if orig == new:
            print(f"# {p}: no change")
            continue
        diff = difflib.unified_diff(
            orig.splitlines(keepends=True), new.splitlines(keepends=True),
            fromfile=p, tofile=p + " (rebranded)",
        )
        sys.stdout.writelines(diff)
