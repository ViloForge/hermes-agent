# Rebrand do-not-touch guard + transform + gate

Deterministic machinery for the **ADR-0003 D4** Constitutional do-not-touch
boundary (`docs/adr/ADR-0003-rebrand-identity-and-tiering.md`) and its
**machine enforcement** (`docs/adr/ADR-0004-machine-enforce-do-not-touch-and-rebrand-test-strategy.md`).
This is the pre-flight gate the rebrand plan requires: **nothing is rebranded
until this exists and is tested**
(`docs/viloforge/plans/2026-06-24-001-rebrand-tiered-plan.md`).

A blind `s/hermes/viloforge/` or `s/nous/viloforge/` breaks the product and
violates the MIT license. The rebrand runs through the tested transform here
(which consults the guard), and every PR is checked by the diff gate.

## Files

| File | Role |
| --- | --- |
| `exclusions.py` | Canonical pattern set + guard API (`protected_spans`, `line_protected`, `path_excluded`, `all_patterns`). Pure stdlib. The single source of truth. |
| `rebrand_apply.py` | **L1** guard-aware brand transform (`rebrand_text`). Replaces `Hermes→ViloForge` display tokens only *outside* protected spans. The codemod every rebrand slice imports — replaces the old throwaway `scratchpad/` apply scripts. |
| `diff_gate.py` | **L2** diff-scoped gate. Fails a PR whose diff contains a *corruption signature* (a protected token in rebranded form, e.g. `x-viloforge-`, `viloforge_cli`). Run locally pre-PR + as the `rebrand-guard` CI job. |
| `scan.py` | Read-only E2E self-check — runs the patterns over the live repo and reports per-pattern coverage + a "trap" review queue. |
| `test_exclusions.py` / `test_rebrand_apply.py` / `test_diff_gate.py` | Contract tests (stdlib `unittest`). Pin behavior, not repo counts. |

## What it encodes

**D4 do-not-touch** — the eight Constitutional exclusion patterns, verbatim,
plus the D4 "trap" host patterns:

| Pattern | D4 | Protects |
| --- | --- | --- |
| `hermes-[0-9]` | D4.2 | Nous Hermes model IDs + the `is_nous_hermes_non_agentic()` guard literal |
| `nous[-_/]hermes` | D4.2 | model family / guard name |
| `Nous Hermes` (title-case), `hermes [0-9]` | D4.2 | model family in **prose** (space form). All-caps `NOUS HERMES` is left rebrandable — it's the cli.py banner (Tier-1 target). |
| `nousresearch` | D4.3/5/8 | URLs, GitHub org, emails, MIT author, live endpoints |
| `NOUS_[A-Z]` | D4.4 | `NOUS_*` env prefix (case-sensitive) |
| `x-nous-` | D4.6 | billing wire-contract headers |
| `psyche`, `atropos` | D4.7 | sibling Nous projects |
| `*.nousresearch.com` host (incl. `hermes-agent.nousresearch.com`) | D4.5 trap | the `hermes` token inside an upstream host is **not** our brand |
| path globs (`plugins/*/nous/**`, `hermes_cli/nous_*`, `proxy/adapters/nous_portal.py`, `agent/portal_tags.py`, `agent/nous_rate_guard.py`) | D4.1 | whole-file Nous Portal provider/auth surface |

**Tier-3 deferred skeleton** (separate, opt-in via `include_tier3=True`) —
`hermes_cli`, `HERMES_[A-Z]`, and the `x-hermes-` HTTP wire-contract headers
(`X-Hermes-Session-Token`/`-Id`/`-Key`/`-Model`; mixed-case, so `HERMES_[A-Z]`
does not catch them — added under ADR-0004). Not do-not-touch (it is ours), but
frozen during the ADR-0002 leash phase, so a Tier-1/2 brand codemod skips it too.
This deferral lifts when ADR-0002's cut trigger fires.

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
python docs/viloforge/rebrand/test_exclusions.py # contract tests (guard)
python docs/viloforge/rebrand/test_rebrand_apply.py  # contract tests (transform)
python docs/viloforge/rebrand/test_diff_gate.py      # contract tests (gate)
```

### Apply the transform (L1) and gate a PR (L2)

```bash
# preview the rebrand of a file (no write):
python docs/viloforge/rebrand/rebrand_apply.py path/to/file.py

# gate the current branch's diff against the do-not-touch boundary:
python docs/viloforge/rebrand/diff_gate.py --base origin/main --head HEAD
git diff origin/main...HEAD | python docs/viloforge/rebrand/diff_gate.py --stdin
```

In code, the transform consults the guard so both share one source of truth:

```python
from rebrand_apply import rebrand_text
new = rebrand_text(original)   # Hermes→ViloForge outside protected spans (leash-aware)
```

The gate runs on every PR as the `rebrand-guard` CI job (`.github/workflows/rebrand-guard.yml`,
wired into `ci.yml`) and **blocks merge** on any corruption. A rare legitimate
hit can be suppressed with an in-line `rebrand-gate: ok` marker (visible in the
diff, so it stays reviewable).

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
