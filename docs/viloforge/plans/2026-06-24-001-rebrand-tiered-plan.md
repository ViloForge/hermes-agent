# Plan 2026-06-24-001: Tiered rebrand execution (hermes-agent → viloforge-agent)

- **Status:** Draft (no rebrand edits started)
- **Date:** 2026-06-24
- **Governed by:** [ADR-0003](../../adr/ADR-0003-rebrand-identity-and-tiering.md)
  (identity, tiers, do-not-touch) · [ADR-0002](../../adr/ADR-0002-upstream-relationship-and-divergence-strategy.md)
  (leash phase → Tier 3 deferred)
- **Baseline verified:** `bc5ae3919`, 2026-06-24, via `git grep`

> This is the **transient delta** (the PBI) — the *how*. The *why* and the binding
> decisions live in ADR-0003; this plan **points at** them and is not the source of
> truth for any decision. When executed, mark `Status: Done`; the ADRs carry the
> durable knowledge forward. Status vocabulary: `Draft | Active | Done | Superseded`.

## Pre-flight (do before Tier 1)

1. **Build the Tier-4 exclusion allowlist** from ADR-0003 D4 — the globset/regex an
   automated pass must skip: `hermes-[0-9]`, `nous[-_/]hermes`, `nousresearch`,
   `plugins/*/nous/**`. Nothing is replaced until this exists and is tested.
2. **Wire the `upstream` remote** (per ADR-0002) and **sync once to upstream HEAD**
   before diverging (ADR-0002 Decision point 4): `git remote add upstream
   https://github.com/NousResearch/hermes-agent.git && git fetch upstream`. Create
   the watch ledger `docs/viloforge/upstream-sync.md`.

## Tier 1 — Display brand (low risk; ship first)

- **Scope:** capitalized "Hermes" product token in **prose/chrome only** — no code
  blocks, no model IDs.
- **Targets:** `README.md`, `README.zh-CN.md`, `README.ur-pk.md`, `apps/desktop/README.md`;
  `assets/banner.png` (image — redraw, not sed); `hermes_cli/banner.py`; the `cli.py`
  framework banner (`"⚕ NOUS HERMES …"` — see edge case below); `website/` + `web/`
  visible strings (EXCLUDE `website/src/data/userStories.json` — contains model refs).
- **Blast radius:** zero import edges. Reviewed hunk-by-hunk.
- **Edge case:** the `cli.py` banner uses "NOUS HERMES". It is *our* banner but
  carries the Nous name — change the product wording, confirm it doesn't touch a
  model-ID path (it doesn't). Flag in review rather than auto-replacing.

## Tier 2 — Package / CLI / Docker / CI identity (medium; deliberate, per-file review)

- **`pyproject.toml`:** `name = "hermes-agent"` → `viloforge-agent`; ~20 extras
  self-refs `hermes-agent[...]`; `[project.scripts]` — **add** `viloforge =
  "hermes_cli.main:main"` *alongside* the existing `hermes` (D2 alias), keep
  `hermes-agent`/`hermes-acp`.
- **8 npm packages** (rename + dependent `import`/workspace refs): root `hermes-agent`,
  `apps/desktop` `hermes`, `@hermes/bootstrap-installer`, `@hermes/shared`,
  `@hermes-agent/photon-sidecar`, `hermes-whatsapp-bridge`, `ui-tui` `hermes-tui`,
  `@hermes/ink` (+ dir `ui-tui/packages/hermes-ink/`). The `@hermes/*` scope rename
  cascades — compute via the workspaces graph before executing.
- **Docker/CI:** Dockerfile/compose image names; `.github/` GHCR publish workflow
  (re-verify live what tag/image it pushes before editing); `.github/actions/hermes-smoke-test/`.
- **Gate:** human review before starting — these are the real product-identity edits.

## Tier 3 — Internal namespace + env prefix — **DEFERRED** (ADR-0002 leash phase)

- **Do NOT** rename `hermes_cli` (4,336 import sites / 1,051 files) or the `HERMES_*`
  prefix (491 vars / 1,138 files) in this effort. `HERMES_*` stays + is aliased (D2).
- Revisit only if/when ADR-0002's cut trigger fires (its own future ADR).

## Sequencing

`Pre-flight → Tier 1 (ship + verify) → Tier 2 (gated) → [Tier 3 deferred]`. One tier
per PR; verify each before the next. Tier 4 is not a step — it is the exclusion
boundary enforced throughout.

## Open execution sub-decision

- **First-sync timing (ADR-0002 point 4 open sub-decision):** sync-to-upstream-HEAD
  before Tier 1 (recommended) vs. rebrand on today's base. Recommendation: sync first.
