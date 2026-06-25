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
   `plugins/*/nous/**`, `NOUS_[A-Z]`, `x-nous-`, `psyche`, `atropos`. Nothing is
   replaced until this exists and is tested. Also handle the D5 legal special-case
   (`apps/desktop/package.json` `legalTrademarks`) deliberately in Tier 2. — ✅
   **done**: `docs/viloforge/rebrand/` (`exclusions.py` guard + `scan.py` E2E
   self-check + `test_exclusions.py` 15 contract tests + README). Adds the D4.5
   trap host patterns and a separate opt-in Tier-3-skeleton layer. Validated at
   HEAD `6d0970c5a`: scan coverage matches the measured blast-radius exactly
   (hermes-[0-9] 49 files, nousresearch 421, NOUS_* 32 vars, psyche 15, atropos
   12, +10 whole-file path excludes); trap report flags 902 brand-near-protected
   lines for hunk-by-hunk review.
2. **Wire the `upstream` remote** (per ADR-0002) and **sync once to upstream HEAD**
   before diverging (ADR-0002 Decision point 4): `git remote add upstream
   https://github.com/NousResearch/hermes-agent.git && git fetch upstream`. Create
   the watch ledger `docs/viloforge/upstream-sync.md`. — ✅ **done** (PR #4, merge
   commit `be87d31b3`, synced through upstream `89540d592`; merge-base advanced,
   divergence now 12). After it landed both the blast-radius counts and the knowledge
   graph go stale at `bc5ae3919` — regenerate before Tier 1 (still pending).
3. **DECISION — upstream syncs land via a merge commit (`--merge`), never a squash.**
   ADR-0002 D4 decided *that* we sync to HEAD but is silent on the git mechanic; this
   is the execution-level fill (correctly here in the plan, not in an immutable ADR —
   per ADR-0003's split of execution detail into the plan). *Rationale:* a true merge
   keeps `main` a descendant of upstream, so the merge-base advances, security
   `cherry-pick -x` retains accurate already-applied ancestry (ADR-0002 point 3), the
   `rev-list --count main..upstream/main` divergence signal stays truthful, and
   upstream authorship survives. A squash leaves upstream commits non-ancestors and
   breaks all four. (Squash stays correct for ordinary contributor feature PRs.) The
   ledger's *Sync procedure* section points here. Recorded 2026-06-24 after PR #4.

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

### Tier 1 — sliced (the `website/`+`web/` surface is 707 files, too big for one PR)

Brand mapping (operator-decided): `Hermes Agent`→`ViloForge Agent`, standalone
`Hermes`→`ViloForge`, `⚕ NOUS HERMES`→`⚕ VILOFORGE`, ASCII logo→`VILOFORGE AGENT`.
Attribution **preserved** + an explicit fork notice added to each README (operator
chose "add a fork notice now"). Scope includes docstrings/comments (operator choice).

- **Tier 1a — core chrome** — ✅ **done** (PR #7): 4 READMEs + `apps/desktop/README.md`
  + `hermes_cli/banner.py` + `cli.py`. 92 guard-checked replacements, hunk-reviewed;
  net protected-token change ≥ 0; 35 banner/skin tests updated + green. The `cli.py`
  "NOUS HERMES" edge case handled (→ VILOFORGE).
- **Tier 1b — `web/` dashboard UI strings** — pending (i18n + components).
- **Tier 1c — `website/` docs prose** — pending (hundreds of `.md`; mostly mechanical;
  EXCLUDE `website/src/data/userStories.json` — model refs).
- **Deferred bits:** `assets/banner.png` redraw (image); native Urdu fork-notice
  translation (currently English with a TODO).

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

### Pre-Tier-2 preview (operator hands-on eval)

Before greenlighting Tier 2, ship a **GHCR `:preview` channel** so the operator
can run the Tier-1 state and evaluate it. Decided **not** as a separate repo —
the fork already builds its image from this repo to `ghcr.io/viloforge/hermes-agent`
(`viloforge-publish.yml`); the registry tag is the distribution unit. Adds a
`:preview` raw tag (on `workflow_dispatch`) + `docker-compose.preview.yml`
(pulls the image, dashboard on `:9119`, isolated throwaway volume) +
`docs/viloforge/preview.md` runbook. Naming = **`preview`** (early/evaluate, not
"release candidate" which implies ship-ready). Scope honesty: the preview is the
Tier-1 *display* brand on the still-`hermes` skeleton (package/command/image name
unchanged — those are Tier 2's job). kb decision `y72sk2pM`.

## Tier 3 — Internal namespace + env prefix — **DEFERRED** (ADR-0002 leash phase)

- **Do NOT** rename `hermes_cli` (4,336 import sites / 1,051 files) or the `HERMES_*`
  prefix (491 vars / 1,138 files) in this effort. `HERMES_*` stays + is aliased (D2).
- Revisit only if/when ADR-0002's cut trigger fires (its own future ADR).

## Sequencing

`Pre-flight → Tier 1 (ship + verify) → Tier 2 (gated) → [Tier 3 deferred]`. One tier
per PR; verify each before the next. Tier 4 is not a step — it is the exclusion
boundary enforced throughout.

## Resolved execution sub-decisions

- **First-sync timing (ADR-0002 point 4 open sub-decision):** ✅ resolved — synced to
  upstream HEAD first (PR #4), then diverge. (Was: sync-first vs. rebrand on today's base.)
- **Sync merge mechanic:** ✅ resolved — `--merge`, never squash (see Pre-flight 3).
