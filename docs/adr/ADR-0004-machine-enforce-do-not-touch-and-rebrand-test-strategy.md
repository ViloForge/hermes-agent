# ADR-0004: Machine-enforce the do-not-touch boundary; rebrand test & enforcement strategy

- **Status:** Accepted
- **Date:** 2026-06-25
- **Deciders:** operator + Claude
- **Constitutional:** no (this *enforces* the Constitutional D4 boundary of
  [ADR-0003](./ADR-0003-rebrand-identity-and-tiering.md); the boundary is inviolable,
  this enforcement mechanism may be revised by a later ADR)

## Context

[ADR-0003 D4](./ADR-0003-rebrand-identity-and-tiering.md) is the Constitutional
do-not-touch boundary: a set of upstream-owned tokens (Nous Hermes model IDs
`hermes-[0-9]`, `NOUS_*`, `x-nous-`, `nousresearch.com`, the MIT author, the Nous
Portal surface) plus our own deferred skeleton (`hermes_cli`, `HERMES_*`, the
`X-Hermes-*` wire-contract headers — Tier 3, kept aligned with upstream per
[ADR-0002](./ADR-0002-upstream-relationship-and-divergence-strategy.md)). Corrupting
any of them breaks the product or violates the license.

Through Tier 1 (PRs #7/#9/#10) that boundary was held by **human hunk-review plus a
manual "net protected-token change ≥ 0" eyeball**, backed by 15 contract tests on the
guard (`docs/viloforge/rebrand/exclusions.py`). Three facts make that insufficient
going forward:

1. **A near-miss already happened.** A `\bHermes\b` rebrand would have corrupted the
   `X-Hermes-*` headers (the brand token sits between hyphens); it was caught only by
   adding `X-Hermes` to the guard mid-effort. The catastrophic failure mode (F1) is
   currently caught only by attention.
2. **The transform logic is throwaway.** Each slice's apply script was re-derived in
   `scratchpad/` (`apply_tier1.py`, `apply_web.py`, …) and re-rolled the same
   word-boundary regexes every time — re-introducing the X-Hermes-class risk on every
   slice. The *guard* was promoted to tested, version-controlled code; the *transform*
   that consumes it was not. That asymmetry is the actual hole.
3. **Display assertions re-break every slice.** Tier 1a broke ~7 scattered
   change-detector tests asserting literal brand strings — exactly the pattern
   `AGENTS.md` forbids ("behavior contracts over snapshots"). Reactively editing
   literals each slice guarantees the cost recurs.

Several more slices remain (Tier 1d residual, Tier 2 identity, and a deferred Tier 3),
so the enforcement question is not one-off. The execution detail (module locations,
function signatures, CI wiring, per-slice checklist) lives in the transient plan
`docs/viloforge/plans/2026-06-24-001-rebrand-tiered-plan.md`, which points at this ADR
rather than restating it.

## Decision

The do-not-touch boundary moves from **human-review-gated** to a **deterministic
machine invariant**, and the rebrand machinery itself becomes tested code.

### D1 — Diff-scoped do-not-touch gate (hard CI + local pre-PR)
A check asserts that **the changeset does not corrupt any inviolable token** — it is a
property of `git diff <merge-base>...HEAD`, not of the tree. It runs **locally before
every rebrand PR and as a CI job that blocks merge** (`docs/viloforge/rebrand/diff_gate.py`,
wired into `ci.yml` via `rebrand-guard.yml`).

The predicate is a **corruption signature**, not "the added line contains a protected
token." That distinction is load-bearing and was corrected during implementation: a
*correctly* rebranded line — e.g. `ViloForge Agent uses hermes_cli` — still carries the
**preserved** protected token `hermes_cli`, so a "line is protected → fail" check would
false-fail correct work and the gate would be disabled. The gate instead flags the
*broken* forms a corrupting codemod produces (`x-viloforge-`, `viloforge-[0-9]`,
`viloforge_cli`, `VILOFORGE_[A-Z]`, `Nous ViloForge`, `viloforge-agent.nousresearch`,
…). These never occur in legitimate code ⇒ ~zero false positives, which is what makes a
hard merge-blocking gate viable. The signatures are **derived from the guard's patterns**
(`exclusions.all_patterns(include_tier3=True)`) + the brand mapping, so the boundary
stays one source of truth; a test pins that every brand-bearing guard pattern has a
signature (so the gate cannot fall behind the guard), and `path_excluded` is honored so
whole-file do-not-touch paths are left to the guard.

The set the gate protects is the subset where corruption is **always** a bug: D4
categories that *contain* a rebrandable brand token (model IDs `hermes-[0-9]`,
`nous[-_/]hermes`, `Nous Hermes`/`Hermes N` prose, the `*.nousresearch.com` infra-host
trap) **plus** the Tier-3-deferred skeleton (`hermes_cli`, `HERMES_*`, `X-Hermes-*`).
Pure-`nous` tokens (`NOUS_*`, `x-nous-`, `nousresearch`, `psyche`/`atropos`) cannot be
produced by a `Hermes→ViloForge` map and need no signature. Fuzzy prose near "Nous
Research" (fork notices, attribution) is **not** gated and stays under human review.

### D2 — The gate is diff-scoped, never a tree-wide count baseline
A whole-repo "protected-token count must not drop below N" gate is explicitly
**rejected**: a count is a snapshot, not a contract — it false-blocks legitimate
upstream syncs (which legitimately shift `nousresearch` counts) and degrades to a
bumpable number that proves nothing. This is the same change-detector anti-pattern
`AGENTS.md` bans. The invariant is "this diff touched no inviolable span," which is
robust to syncs and needs no baseline.

### D3 — The rebrand transform is tested, version-controlled code
The replacement logic is promoted out of `scratchpad/` into a tested helper that
**consumes the guard** (`protected_spans`/`line_protected`). Its regex edge cases
(`X-Hermes`, `HermesCLI`, `hermes-3`, the fork-notice context) are unit-tested once and
reused by every remaining slice, instead of being re-derived per slice.

### D4 — Rebrand tests assert behavior, not brand literals (apply existing policy)
Display-string change-detector tests are converted to behavioral invariants
**opportunistically and in-scope** — only the tests in the slice being worked, and only
where the literal is genuine chrome. Parameterized/functional uses (e.g. a name passed
as an argument) and out-of-scope plugin tests are left alone. No new change-detector or
count-baseline tests are introduced. This is application of the existing `AGENTS.md`
rule, recorded here because it is now a standing part of the rebrand's definition of
done.

## Consequences

- **+** F1 (corrupting the inviolable surface) moves from "caught by attention" to
  "cannot merge" — the catastrophic, license-bearing failure mode is machine-enforced.
- **+** One source of truth: the apply-time avoidance, the CI gate, and the contract
  tests all run off `exclusions.py`. A boundary change is one edit.
- **+** The change-detector test surface shrinks slice by slice instead of recurring.
- **+** The gate is sync-safe: because it is diff-scoped against the merge base, the
  `--merge` upstream syncs (ADR-0002 / plan Pre-flight 3) do not trip it.
- **−** Small permanent additions to maintain: one tested transform helper + a ~40-line
  gate + a CI job. (Mitigated: both reuse the already-tested guard.)
- **−** The gate enforces only the *inviolable* subset; fuzzy attribution prose still
  needs human review (by design — automating it would false-block fork notices).
- **Neutral:** non-Constitutional — a later ADR may revise the mechanism (e.g. widen
  the gate's pattern set for Tier 2's deliberate package-file edits) without touching
  the D4 boundary it protects.

## Alternatives Considered

- **Keep manual hunk-review only** — rejected: it is the status quo that nearly let the
  X-Hermes corruption through, and it does not scale across the remaining slices.
- **Tree-wide protected-token count baseline** — rejected (D2): a change-detector
  snapshot that false-blocks upstream syncs and proves nothing once bumpable.
- **Local pre-PR check without a CI gate** — rejected: relies on remembering to run it;
  a merge-blocking invariant is what converts discipline into a guarantee.
- **Big-bang conversion of all ~27 display-assertion tests now** — rejected (D4): a
  large standalone refactor that touches plugin tests outside the current rebrand
  scope; opportunistic in-scope conversion retires the debt without the churn.
- **Record this as plan-only (no ADR)** — rejected: moving a Constitutional boundary's
  enforcement from human to machine is a durable trust-model decision, which is what the
  ADR layer is for; the execution mechanics still live in the plan.
