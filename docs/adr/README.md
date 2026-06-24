# ViloForge Agent — architecture decisions (fork ADR log)

Immutable Architecture Decision Records for the **ViloForge fork** of Nous
Research's `hermes-agent` (rebranding to `viloforge-agent`). These records govern
the **fork-level** choices a casual reader of the code cannot recover: our
relationship to upstream, the rebrand strategy and its tiers, compatibility
guarantees, and what we deliberately diverge on.

These live **in this repo** (Nygard default — "ADRs live with the code they
govern"). Unlike the clean-room vfwms/pybadi log (which is spec-side so the wright
cannot rewrite its own rules), this fork has no clean-room membrane: the operator
edits both code and ADRs, so co-location is correct and maximally discoverable.

## How it works

Same practice as the rest of the ViloForge ADR logs (see
[`vfwms/spec/adr`](https://github.com/ViloForge) and `vfwms-forge/docs/adr`):

- **Nygard shape** — Status / Date / Deciders / Constitutional, then
  Context / Decision / Consequences / Alternatives Considered.
- **Immutable once Accepted.** A change of mind is a **new ADR that supersedes**
  the old one (old status → `Superseded by ADR-NNNN`). Never edit an Accepted ADR
  in place — that loses the evolution of thinking (decision amnesia).
- **Sequential numbering** `ADR-NNNN`, assigned at merge to `main`. Solo/linear
  repo → a counter is collision-free.
- **`Constitutional: yes`** flags a load-bearing rule that constrains future work
  (e.g. "DO NOT rebrand upstream model IDs"). LLMs underweight "DO NOT", so a
  constitutional negation that matters should also get a deterministic check, not
  just prose.
- **One decision per ADR.** Small/fast choices stay inline in code or `docs/`.
  Only decision-grade, hard-to-recover choices earn an ADR.

## Status vocabulary

`Proposed` (drafted, not yet ratified by the operator) · `Accepted` ·
`Superseded by ADR-NNNN` · `Rejected`.

## Log

| ADR | Title | Status |
| --- | --- | --- |
| [0001](./ADR-0001-record-viloforge-fork-decisions-as-adrs.md) | Record ViloForge fork decisions as immutable ADRs, in-repo | Accepted |
| [0002](./ADR-0002-upstream-relationship-and-divergence-strategy.md) | Upstream relationship — the leash phase (diverge-and-reimplement; hard cut deferred to a triggered future ADR) | Accepted |
| [0003](./ADR-0003-rebrand-identity-and-tiering.md) | Rebrand identity (`viloforge-agent`/`viloforge`), four-tier ordering, deprecated aliases, and the do-not-touch boundary | Accepted |
