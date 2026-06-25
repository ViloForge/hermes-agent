"""Tier-4 do-not-touch exclusion allowlist for the ViloForge rebrand.

Deterministic implementation of the **ADR-0003 D4** constitutional boundary
(``docs/adr/ADR-0003-rebrand-identity-and-tiering.md``). Any automated
``hermes``/``nous`` rebrand pass (sed, codemod) MUST consult this module and
skip the surfaces it flags — corrupting them breaks provider auth, the model
non-agentic guard, the Nous billing wire contract, or the MIT license
attribution.

Pure stdlib (no third-party imports) so it runs in any environment and is
independent of the test tree / CI. The companion ``scan.py`` runs it against
the live repo; ``test_exclusions.py`` pins the contract.

Two layers:

* **D4 do-not-touch** — the eight Constitutional exclusion patterns enumerated
  in ADR-0003 D4, plus the explicit "trap" host patterns D4 calls out in prose
  (``hermes`` *inside* a ``*.nousresearch.com`` host is upstream infra, not our
  brand). These are upstream property — never rebranded, ever.
* **Tier-3 deferred skeleton** — ``hermes_cli`` / ``HERMES_<UPPER>``. NOT
  upstream property (it is ours), but kept aligned with upstream during the
  ADR-0002 leash phase, so a Tier-1/2 brand codemod must also skip it for now.
  Tracked separately because the *reason* differs (deferral, not do-not-touch)
  and it lifts when ADR-0002's cut trigger fires.

A match protects a **span**, and by extension the line it sits on. Protection
is deliberately conservative: when a line carries both a rebrandable ``Hermes``
brand token *and* a protected token (e.g. ``hermes-agent.nousresearch.com``),
the safe default is to skip the whole line and let human review catch any
under-rebrand — never to risk corrupting the protected token.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fnmatch import fnmatch
from typing import List, Tuple


@dataclass(frozen=True)
class ContentPattern:
    name: str
    regex: "re.Pattern[str]"
    d4_category: str  # which ADR-0003 D4 category (or "trap"/"tier3") this implements
    note: str


@dataclass(frozen=True)
class PathGlob:
    glob: str
    d4_category: str
    note: str


# --- D4: the eight Constitutional exclusion patterns (ADR-0003 D4 bullet list) ---
# Implemented verbatim. IGNORECASE except the NOUS_ env prefix, which is a
# case-significant identifier (uppercase wire/config contract).
_D4_CONTENT: List[ContentPattern] = [
    ContentPattern(
        "hermes-model-id",
        re.compile(r"hermes-[0-9]", re.IGNORECASE),
        "D4.2",
        "Nous Hermes LLM model IDs (hermes-3, hermes-4, deephermes-3, "
        "hermes-4.3-36b, ...). model_switch.is_nous_hermes_non_agentic() depends "
        "on the literal string.",
    ),
    ContentPattern(
        "nous-hermes",
        re.compile(r"nous[-_/]hermes", re.IGNORECASE),
        "D4.2",
        "nousresearch/hermes-*, nous_hermes, Nous-Hermes — model family + the "
        "is_nous_hermes_non_agentic guard name.",
    ),
    # D4.2 prose space-forms: the model family is also written "Nous Hermes" and
    # "Hermes 3"/"Hermes 4" in prose (space, not the hyphen the patterns above
    # catch). A `\bHermes\b`→ViloForge codemod would corrupt these upstream model
    # references ("Nous ViloForge", "ViloForge 3"). Conservative over-protection:
    # under-rebrand here is caught by the per-slice completeness check (L3); a
    # corrupted model reference is not. (Extends D4.2 enforcement beyond the
    # hyphenated patterns ADR-0003 lists — operator-ratifiable.)
    ContentPattern(
        "nous-hermes-spaced",
        # Case-SENSITIVE on purpose: protects the prose model family "Nous Hermes"
        # but NOT the all-caps cli.py banner "NOUS HERMES", which ADR-0003 Tier 1
        # designates a rebrand target (→ VILOFORGE). Same letters, different
        # meaning; case is the only signal that separates them.
        re.compile(r"Nous\s+Hermes"),
        "D4.2",
        "'Nous Hermes' model family in prose (title-case space form). The all-caps "
        "'NOUS HERMES' banner is intentionally NOT matched (it is a Tier-1 target).",
    ),
    ContentPattern(
        "hermes-model-spaced",
        re.compile(r"hermes\s+[0-9]", re.IGNORECASE),
        "D4.2",
        "'Hermes 3'/'Hermes 4' model family in prose (space-separated form).",
    ),
    ContentPattern(
        "nousresearch",
        re.compile(r"nousresearch", re.IGNORECASE),
        "D4.3/5/8",
        "nousresearch.com URLs, NousResearch GitHub org, @nousresearch.com "
        "emails, MIT author, live endpoints — all upstream property.",
    ),
    ContentPattern(
        "nous-env-prefix",
        re.compile(r"NOUS_[A-Z]"),  # case-sensitive: the env/config namespace
        "D4.4",
        "NOUS_* env prefix (~32 vars: NOUS_API_KEY, NOUS_CLIENT_ID, "
        "NOUS_PORTAL_URL, ...). Distinct from our HERMES_*.",
    ),
    ContentPattern(
        "x-nous-header",
        re.compile(r"x-nous-", re.IGNORECASE),
        "D4.6",
        "x-nous-credits-* HTTP response headers — the Nous billing wire contract.",
    ),
    ContentPattern(
        "psyche",
        re.compile(r"psyche", re.IGNORECASE),
        "D4.7",
        "Nous Research sibling project name (github.com/NousResearch/psyche).",
    ),
    ContentPattern(
        "atropos",
        re.compile(r"atropos", re.IGNORECASE),
        "D4.7",
        "Nous Research sibling project name (github.com/NousResearch/atropos).",
    ),
    # --- D4 prose "trap": hermes inside a *.nousresearch.com host is upstream
    # infra, not our brand. The bare `nousresearch` pattern above protects the
    # span only; these host patterns extend the protected span to include the
    # leading `hermes` token so a span-aware codemod cannot rewrite the host.
    ContentPattern(
        "trap-host-hermes-agent",
        re.compile(r"hermes-agent\.nousresearch\.com", re.IGNORECASE),
        "D4.5-trap",
        "hermes-agent.nousresearch.com / setup.hermes-agent... — upstream infra "
        "host; the hermes token here is NOT our brand.",
    ),
    ContentPattern(
        "trap-host-docs-hermes-agent",
        re.compile(r"hermes--agent\.nousresearch\.com", re.IGNORECASE),
        "D4.5-trap",
        "docs-hermes--agent.nousresearch.com — upstream docs host variant.",
    ),
]

# --- D4 path globs (whole file is upstream property — skip entirely) ---
# D4 lists `plugins/*/nous/**` as the one glob; D4.1 prose names the rest of the
# Nous Portal provider/auth surface explicitly. Encoded as path denies so a
# codemod skips these files wholesale.
_D4_PATHS: List[PathGlob] = [
    PathGlob("plugins/*/nous/**", "D4.1", "Nous Portal provider/auth plugin surface."),
    PathGlob("plugins/*/nous/*", "D4.1", "Nous Portal provider/auth plugin surface (direct children)."),
    PathGlob("hermes_cli/nous_*", "D4.1", "hermes_cli/nous_* — Nous auth/portal modules."),
    PathGlob("proxy/adapters/nous_portal.py", "D4.1", "Nous Portal proxy adapter."),
    PathGlob("agent/portal_tags.py", "D4.1", "Nous Portal request tagging."),
    PathGlob("agent/nous_rate_guard.py", "D4.1", "Nous rate guard."),
]

# --- Tier-3 deferred skeleton (ADR-0003 D3 Tier 3 / ADR-0002 leash) ---
# NOT do-not-touch; ours, but frozen during the leash phase. A Tier-1/2 brand
# codemod skips these so it cannot corrupt the upstream-aligned skeleton.
_TIER3_CONTENT: List[ContentPattern] = [
    ContentPattern(
        "hermes_cli-namespace",
        re.compile(r"hermes_cli"),
        "tier3",
        "Internal Python namespace — kept aligned with upstream (4,724 import "
        "sites). Rename deferred per ADR-0002.",
    ),
    ContentPattern(
        "HERMES-env-prefix",
        re.compile(r"HERMES_[A-Z]"),
        "tier3",
        "HERMES_* env prefix (496 vars) — kept + aliased per ADR-0003 D2, not "
        "renamed during the leash.",
    ),
    ContentPattern(
        "x-hermes-header",
        re.compile(r"x-hermes-", re.IGNORECASE),
        "tier3",
        "X-Hermes-* HTTP headers (X-Hermes-Session-Token/-Id/-Key/-Model) — our "
        "web/API wire contract (web/src/lib/api.ts <-> hermes_cli/web_server.py). "
        "Part of the HERMES_* skeleton kept aligned with upstream during the leash; "
        "mixed-case so HERMES_[A-Z] does not catch it. A \\bHermes\\b codemod would "
        "corrupt the header (brand token sits between hyphens).",
    ),
]


def _glob_match(relpath: str, glob: str) -> bool:
    # fnmatch's `*` spans `/`, so `plugins/*/nous/**` already matches nested
    # paths; we also match the literal-children form for clarity.
    return fnmatch(relpath, glob)


def path_excluded(relpath: str) -> Tuple[bool, str]:
    """Is this whole file off-limits to a rebrand codemod?

    Returns (excluded, reason). The Tier-3 skeleton is enforced at content level
    (see ``protected_spans``), not path level — so there is no tier3 toggle here.
    """
    rp = relpath.replace("\\", "/").lstrip("./")
    for pg in _D4_PATHS:
        if _glob_match(rp, pg.glob):
            return True, f"{pg.d4_category}: {pg.note} [{pg.glob}]"
    return False, ""


def protected_spans(text: str, include_tier3: bool = False) -> List[Tuple[int, int, str]]:
    """Char spans in `text` that a rebrand codemod must not rewrite.

    Returns a list of (start, end, pattern_name), sorted by start. With
    `include_tier3=True`, also protects the deferred ``hermes_cli`` / ``HERMES_*``
    skeleton (for Tier-1/2 codemods running during the leash phase).
    """
    patterns = list(_D4_CONTENT)
    if include_tier3:
        patterns += _TIER3_CONTENT
    spans: List[Tuple[int, int, str]] = []
    for pat in patterns:
        for m in pat.regex.finditer(text):
            spans.append((m.start(), m.end(), pat.name))
    spans.sort()
    return spans


def line_protected(text: str, include_tier3: bool = False) -> bool:
    """Conservative line-level guard: True if any protected span is present."""
    return bool(protected_spans(text, include_tier3=include_tier3))


def all_patterns(include_tier3: bool = False) -> List[ContentPattern]:
    return list(_D4_CONTENT) + (list(_TIER3_CONTENT) if include_tier3 else [])


def all_path_globs() -> List[PathGlob]:
    return list(_D4_PATHS)
