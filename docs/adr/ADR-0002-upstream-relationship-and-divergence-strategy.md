# ADR-0002: Upstream relationship — the leash phase (diverge-and-reimplement, hard cut deferred)

- **Status:** Proposed
- **Date:** 2026-06-24
- **Deciders:** operator + Claude
- **Constitutional:** yes (governs how every change relates to upstream *during the leash phase*)

> **Proposed** — this ADR records the recommended decision and its alternatives for
> operator ratification. It deliberately replaces an ad-hoc "pick an option" prompt:
> the decision is made *by accepting/editing this record*, not in chat.

## Context

The fork is currently upstream HEAD + 2 fork-specific commits — near-zero
divergence (verified 2026-06-24: `origin` = `viloforge/hermes-agent`; upstream
`NousResearch/hermes-agent` main = `8446c1570`, reachable and already ahead of our
base). We intend a **deep rebrand** to `viloforge-agent`, and the operator's stated
end-state is to *"diverge and ultimately cut off the fork, then periodically study
NousResearch's improvements and reimplement them in our version."*

Two forces shape the path to that end-state:

- **The more we rebrand, the costlier upstream integration becomes.** Every renamed
  file/symbol/string is a merge-conflict magnet. Renaming the internal namespace
  `hermes_cli` (4,336 import sites across 1,051 files) or the `HERMES_*` env prefix
  (491 vars across 1,138 files) would make almost every upstream cherry-pick conflict.
- Upstream ships fast (continuous PRs) and includes **security fixes** in
  credential/provider/network/MCP code. Losing cheap access to those is the main
  risk of cutting the cord *too early*.

**The key insight (the reason this ADR was revised before ratification):** the hard
cut is a *destination*, not a *starting move*. There is a transitional period — the
**leash phase** — where keeping a thin tie to upstream is cheap and the security
optionality is valuable. This ADR governs **that phase** and names the **trigger**
that ends it. It deliberately does **not** pre-decide the cut itself; that is a
separate future decision (see "The hard cut is a deferred decision" below).

## Decision (proposed)

Adopt, **for the leash phase**, a **hard fork with a thin compatibility leash** —
upstream is a *watched reference we reimplement from*, not a branch we routinely merge:

1. **Diverge freely on the product surface** — brand, UX, packaging, product
   features. No obligation to stay merge-compatible there.
2. **Keep the internal skeleton aligned with upstream — *for the duration of the
   leash phase only*.** Do **not** rename `hermes_cli` or the `HERMES_*` env prefix
   *yet* (`HERMES_*` is kept and aliased per the rebrand ADR; the namespace is kept
   as-is). The rationale is **cognitive mapping**: when we read an upstream fix in
   `hermes_cli/auth.py` we want it to land at the same place in our tree so
   reimplementation takes minutes, not a reverse-engineering session — and so
   security cherry-picks still apply cleanly. **This freeze expires at the cut**
   (point 5); it is *not* a permanent constitutional bar on renaming the namespace.
3. **Keep the leash, don't cut it (yet):**
   - Wire and retain an `upstream` git remote
     (`https://github.com/NousResearch/hermes-agent.git`). Cutting the *merge*
     relationship is not deleting the *linkage* — `git log <studied-sha>..upstream/main`
     remains the cheapest way to discover what changed.
   - Maintain an **upstream-watch ledger** (`docs/viloforge/upstream-sync.md`):
     last-studied upstream SHA + date, what we reimplemented, what we deliberately
     skipped, and security items flagged/ported. Review on a cadence (e.g. monthly).
   - Retain the **option** to `git cherry-pick -x` directly into the un-rebranded,
     security-sensitive subsystems (auth, provider adapters, egress, MCP) — they
     stay merge-clean precisely because we have not rebranded them.
4. **Sync once to current upstream HEAD before the rebrand begins**, then diverge.
   This is the last cheap merge; starting divergence from `8446c1570` (vs. an
   already-aging base) maximizes the value of the leash phase.
5. **The leash is transitional, ended by a defined trigger — not a date.** The leash
   stays on while alignment *buys* more than it *costs*: cheap security backports +
   cheap reimplementation mapping. It is cut when alignment becomes a **tax** —
   evaluated at each upstream-watch cadence against these conditions (any one is
   sufficient):
   - **Alignment blocks the product**: staying skeleton-aligned with upstream
     prevents a change we want (e.g. a `hermes_cli` → `viloforge_cli` rename, a
     structural refactor upstream won't take).
   - **Upstream relevance decays**: over a sustained window (e.g. two cadences) we
     pull ~zero fixes worth reimplementing and no security items — the leash is
     paying for optionality we no longer use.
   - **Divergence outgrows the map**: the trees have drifted enough that "read the
     upstream fix, find the spot in ours" no longer works, so structural alignment
     has stopped delivering its only benefit.
   When the trigger fires, we ratify the cut in its own ADR (next).

## The hard cut is a deferred decision (YAGNI / build-to-need)

We deliberately do **not** specify the post-cut world here — severing the `upstream`
remote, deep-renaming the internal namespace, dropping the watch ledger. Pre-deciding
a state we are not in would over-constrain it and likely be wrong by the time we
arrive. When the point-5 trigger fires, the hard cut is recorded as a **future ADR
that supersedes the leash-phase clauses of this one** (this ADR's status would then
move to `Superseded by ADR-NNNN` for those clauses). Until then, the leash phase is
the standing policy.

## Consequences

- **+** Full rebrand freedom on the product surface *now*, with a clear, triggered
  path to total independence later.
- **+** Security fixes remain *reachable* during the leash phase two ways:
  cherry-pick into un-rebranded subsystems, or guided reimplementation via the
  ledger + structural alignment.
- **+** No standing merge-conflict tax; we adopt upstream selectively, on our cadence.
- **+** The namespace freeze is correctly scoped — a future reader after the cut is
  not misled into thinking `hermes_cli` can never be renamed.
- **−** Reimplementation is more expensive per-fix than a merge, and we trail
  upstream on velocity by design.
- **−** Requires *discipline*: the watch cadence and ledger are load-bearing. If the
  ledger lapses, "study and reimplement" silently degrades into "diverge and go
  blind" — the actual failure mode to avoid. The ledger is also where the point-5
  trigger conditions are actually evaluated.
- **Neutral:** during the leash phase, keeping the skeleton aligned constrains how
  deep the rebrand goes (Tier 3 stays deferred) — already the recommendation for
  other reasons. This constraint lifts at the cut.

## Alternatives Considered

- **Full hard cut *now*** (delete the upstream remote immediately, pure
  reimplementation, rebrand everything including the namespace from day one) —
  rejected: maximizes independence but also maximizes security exposure and
  reimplementation cost *while divergence is still small and a leash is nearly free*,
  and throws away the discovery tool (`git log ..upstream/main`). The cut is the
  right *destination*, not the right *first move*. This ADR keeps it as a triggered
  future step (point 5), not a rejected idea.
- **Continuous backport-merge forever** (stay merge-compatible, shallow rebrand,
  regularly merge `upstream/main`) — rejected as the *primary* model: it caps how
  far we can rebrand and imposes a permanent conflict tax. Retained only as the
  *fallback mechanism* for the un-rebranded security-sensitive subsystems during the
  leash phase (point 3).
- **Vendor/patch-set model** (upstream as a pinned dependency + a patch series) —
  rejected: `hermes-agent` is a monorepo application, not a library we consume;
  there is no clean dependency boundary to pin.
- **Indefinite leash (no defined end)** — rejected: an open-ended leash quietly
  becomes "continuous backport-merge forever" by default, never reaching the
  operator's stated end-state. The point-5 trigger forces a periodic, explicit
  "cut or keep" decision instead of drift.

## Open sub-decision

- **Cut timing for the *first* sync (point 4):** sync-to-HEAD-then-rebrand
  (recommended) vs. rebrand on today's base. Recommendation: sync first. *(This is
  about the one-time pre-rebrand sync, not the hard cut — the hard cut's timing is
  governed by the point-5 trigger.)*
