# ADR-0001: Record ViloForge fork decisions as immutable ADRs, in-repo

- **Status:** Accepted
- **Date:** 2026-06-24
- **Deciders:** operator + Claude
- **Constitutional:** no (this is the practice that governs the log)

## Context

This repository is the **ViloForge fork** of Nous Research's `hermes-agent`
(PyPI `hermes-agent`, MIT, author "Nous Research"). The goal is to rebrand it to
`viloforge-agent` and run it as our own product. As of this ADR the fork is
upstream HEAD + 2 commits (a GHCR publish workflow and an author-email map) — near
zero divergence — so every load-bearing fork-level choice is still ahead of us:

- **how we relate to upstream** (keep merging fixes vs. hard-fork and reimplement);
- **the rebrand strategy** — which surfaces become `viloforge`, which stay
  `hermes_cli`/`HERMES_*` for compatibility, and which upstream references
  (Nous Portal provider auth, `hermes-3/4` model IDs, MIT attribution) must
  **never** be touched;
- **compatibility guarantees** (deprecated aliases vs. hard cut).

These are exactly the choices a future reader of the diff cannot reconstruct — they
are *why* decisions, and getting one wrong (e.g. a blind `sed` over `hermes`) breaks
provider auth or violates the license. Recording them ad hoc (commit messages, kb,
chat) loses the rationale and the alternatives we rejected. We already run a mature
ADR practice elsewhere in ViloForge (`vfwms/spec/adr`, `vfwms-forge/docs/adr`,
Nygard format) and align with it here.

## Decision

- Record **significant** fork-level decisions as **immutable ADRs** in
  **`docs/adr/`** of *this* repo, in **Nygard format**
  (Status / Date / Deciders / Constitutional, then
  Context / Decision / Consequences / Alternatives Considered).
- **Immutable once Accepted.** A change of mind is a **new ADR that supersedes** the
  old one (old status → `Superseded by ADR-NNNN`); ADRs are never edited in place.
- **Numbering:** plain sequential `ADR-NNNN`, assigned at merge to `main`. Solo,
  linear, single-writer repo → a counter is collision-free.
- **`Constitutional: yes`** flags an ADR whose rule is load-bearing enough that
  later work (including automated rebrand passes) must not violate it — e.g.
  "do not rebrand the `nous`/`hermes-3/4` upstream surface". Where feasible, back a
  constitutional negation with a deterministic check (an exclusion allowlist /
  lint), since "DO NOT" rules are easy to forget.
- **Scope:** decision-grade, hard-to-recover choices only. Mechanical detail,
  file-by-file rebrand lists, and working notes stay in `docs/` plans (e.g. the
  tiered rebrand plan), not in ADRs. kb holds a one-line pointer to each ADR.

## Why in-repo, not spec-side

The vfwms/pybadi ADR log lives spec-side specifically so the clean-room **wright**
cannot edit its own constitution — a *physical* membrane. This fork has **no such
membrane**: the operator edits code and ADRs alike. So the Nygard default ("ADRs
live with the code they govern") applies, and co-location maximizes discoverability
and travels with the code on clone. The operator explicitly required the ADRs be
kept in the repo.

## Consequences

- **+** Fork-level rationale (especially the do-not-touch upstream boundaries) is
  preserved and versioned; survives `git clean`; travels on clone.
- **+** Future rebrand passes — manual or automated — have a citable contract
  ("violates ADR-NNNN") instead of tribal memory.
- **+** Decouples *decisions* (ADRs, stable) from *plans* (`docs/`, churn-y).
- **−** Ceremony: one record per significant decision.
- **Neutral:** kb still holds decisions too, but now as **pointers** to the
  authoritative in-repo ADR, not as the system of record for fork architecture.

## Alternatives Considered

- **kb as the system of record** — rejected for *architecture* decisions: kb is
  great for atomic facts/handoffs but is not versioned with the code, does not
  travel on clone, and is not reviewable in a PR diff. kb keeps a pointer instead.
- **A single `DECISIONS.md` with an edit-in-place list** — rejected: loses history
  and the evolution of thinking (the classic failure ADRs exist to prevent).
- **Spec-side / external ADR repo** (as in vfwms) — rejected: no clean-room wright
  here to wall off, and the operator wants the records to ship with the fork.
