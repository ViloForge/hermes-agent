# Tier-4 do-not-touch exclusion allowlist

Deterministic guard for the **ADR-0003 D4** Constitutional do-not-touch boundary
(`docs/adr/ADR-0003-rebrand-identity-and-tiering.md`). This is the pre-flight
gate the rebrand plan requires: **nothing is rebranded until this exists and is
tested** (`docs/viloforge/plans/2026-06-24-001-rebrand-tiered-plan.md`,
Pre-flight 1).

A blind `s/hermes/viloforge/` or `s/nous/viloforge/` breaks the product and
violates the MIT license. Any automated rebrand pass (sed, codemod) MUST consult
this allowlist and skip what it flags.

## Files

| File | Role |
| --- | --- |
| `exclusions.py` | Canonical pattern set + guard API. Pure stdlib. The source of truth a codemod imports. |
| `scan.py` | Read-only E2E self-check — runs the patterns over the live repo and reports per-pattern coverage + a "trap" review queue. |
| `test_exclusions.py` | Contract tests (stdlib `unittest`). Pins behavior, not repo counts. |

## What it encodes

**D4 do-not-touch** — the eight Constitutional exclusion patterns, verbatim,
plus the D4 "trap" host patterns:

| Pattern | D4 | Protects |
| --- | --- | --- |
| `hermes-[0-9]` | D4.2 | Nous Hermes model IDs + the `is_nous_hermes_non_agentic()` guard literal |
| `nous[-_/]hermes` | D4.2 | model family / guard name |
| `nousresearch` | D4.3/5/8 | URLs, GitHub org, emails, MIT author, live endpoints |
| `NOUS_[A-Z]` | D4.4 | `NOUS_*` env prefix (case-sensitive) |
| `x-nous-` | D4.6 | billing wire-contract headers |
| `psyche`, `atropos` | D4.7 | sibling Nous projects |
| `*.nousresearch.com` host (incl. `hermes-agent.nousresearch.com`) | D4.5 trap | the `hermes` token inside an upstream host is **not** our brand |
| path globs (`plugins/*/nous/**`, `hermes_cli/nous_*`, `proxy/adapters/nous_portal.py`, `agent/portal_tags.py`, `agent/nous_rate_guard.py`) | D4.1 | whole-file Nous Portal provider/auth surface |

**Tier-3 deferred skeleton** (separate, opt-in via `include_tier3=True`) —
`hermes_cli` and `HERMES_[A-Z]`. Not do-not-touch (it is ours), but frozen
during the ADR-0002 leash phase, so a Tier-1/2 brand codemod skips it too. This
deferral lifts when ADR-0002's cut trigger fires.

## Usage

```python
from exclusions import path_excluded, protected_spans, line_protected

# whole-file skip?
skip, reason = path_excluded("plugins/foo/nous/adapter.py")

# span-aware: rewrite brand tokens only OUTSIDE these char ranges
spans = protected_spans(line, include_tier3=True)   # leash phase: skip skeleton too

# coarse line guard
if line_protected(line, include_tier3=True):
    ...  # leave the line for human review
```

```bash
python docs/viloforge/rebrand/scan.py            # coverage table
python docs/viloforge/rebrand/scan.py --traps    # brand-near-protected review queue
python docs/viloforge/rebrand/test_exclusions.py # contract tests
```

## Validation (as of HEAD `6d0970c5a`, post-PR-#4)

`scan.py` coverage matches the independently-measured blast-radius exactly:
`hermes-[0-9]` 49 files, `nous[-_/]hermes` 14, `nousresearch` 421, `NOUS_*` 32
distinct vars / 48 files, `x-nous-` 12, `psyche` 15, `atropos` 12; 10 whole-file
path exclusions; `HERMES_*` 496 distinct vars (Tier-3 deferred). The trap report
flags 902 lines (mostly upstream `github.com/NousResearch/hermes-agent` URLs) for
hunk-by-hunk human review — the exact discipline Tier 1 mandates.

## Conservative-by-design

When a line carries both a rebrandable `Hermes` brand token and a protected
token, the safe default is to skip the whole line (or rewrite only outside the
protected spans) and let human review catch any under-rebrand. Under-rebranding
is safe; corrupting a protected token is not.
