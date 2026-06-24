# ADR-0003: Rebrand identity, tiering, and the do-not-touch boundary

- **Status:** Proposed
- **Date:** 2026-06-24
- **Deciders:** operator + Claude
- **Constitutional:** yes (the do-not-touch boundary and the tier ordering bind every rebrand edit)

> **Proposed** — most of this ADR records decisions the operator *already made* in
> session (brand name, deprecated aliases) plus the verified do-not-touch boundary
> already shipped in `AGENTS.md`. It is `Proposed` only so the operator gives the
> synthesized whole one look before it becomes immutable + Constitutional. Ratify by
> accepting (or editing) this record.

## Context

This is the ViloForge fork of Nous Research's `hermes-agent`, being rebranded to
`viloforge-agent`. The string `hermes` appears **55,231 times across 3,150 files**
(verified 2026-06-24 at `bc5ae3919` via `git grep`). A blind find/replace is
impossible: `hermes` is **four distinct things**, and one of them is upstream
property whose corruption breaks the product and violates the MIT license.

The upstream relationship is fixed by **[ADR-0002](./ADR-0002-upstream-relationship-and-divergence-strategy.md)**
(Accepted — the *leash phase*): during this phase we keep the internal skeleton
(`hermes_cli`, the `HERMES_*` env prefix) aligned with upstream so security fixes
stay reimplementable. **That directly sets how deep this rebrand goes** — Tier 3
(below) is deferred *because* of ADR-0002. When ADR-0002's cut trigger fires, the
Tier 3 deferral may be revisited by that future ADR.

Identifiers and counts cited here are the permanent decision record; the **execution
detail** (exact file/glob lists, per-tier steps, ordering, status) lives in the
transient plan `docs/viloforge/plans/2026-06-24-001-rebrand-tiered-plan.md`, which
*points at this ADR* rather than restating it (single source of truth).

## Decision

### D1 — Brand identity (operator-decided)
- PyPI / product package name → **`viloforge-agent`**.
- Primary console command → **`viloforge`**.

### D2 — Backward compatibility: deprecated aliases, not a hard cut (operator-decided)
- The old `hermes` console command **and** the entire `HERMES_*` environment-variable
  prefix (491 distinct vars across 1,138 files) are kept as **deprecated aliases**
  (dual-read; emit a deprecation warning) for **≥1 release**.
- **No hard cut** of either. A hard cut would silently break every deployed user
  config, systemd unit, Docker env, and shell script.

### D3 — Four tiers, executed in this order
The rebrand is partitioned into four tiers; lower tiers ship first (low risk →
high), each human-gated. Tiers are *categories of `hermes`*, not directories:

1. **Tier 1 — Display brand** (low risk; do first). User-visible product name in
   prose/chrome: READMEs, `assets/banner.png`, `hermes_cli/banner.py`, the `cli.py`
   framework banner, website/web visible strings. Capitalized "Hermes" token, prose
   only, no code/model-IDs. Zero import-edge blast radius.
2. **Tier 2 — Package / CLI / Docker / CI identity** (medium; the real product
   decisions). `pyproject.toml` name + extras + entrypoints (add `viloforge`
   alongside `hermes` per D2); the 8 npm package names; Dockerfile/compose image;
   GHCR publish workflow + `.github/actions/hermes-smoke-test`.
3. **Tier 3 — Internal namespace + env prefix** (high churn; **DEFERRED** per
   ADR-0002). `hermes_cli` (4,336 import sites across 1,051 files) and `HERMES_*`
   are **kept aligned with upstream** during the leash phase; `HERMES_*` is kept and
   aliased per D2. **Do not rename the internal `hermes_cli` namespace while the
   leash is on.**
4. **Tier 4 — Do-not-touch** (see D4).

### D4 — Constitutional do-not-touch boundary
The following are upstream property, **not ours** — never rebranded; any automated
pass MUST exclude them, and a deterministic exclusion allowlist gates the work.
*(Expanded 2026-06-24 after a six-lens adversarial completeness sweep; categories
4–8 were found missing from the first draft.)*

1. **Nous Portal provider & auth** — `plugins/*/nous/`, `hermes_cli/nous_*`,
   `proxy/adapters/nous_portal.py`, `agent/portal_tags.py`, `agent/nous_rate_guard.py`.
2. **Nous Hermes LLM model IDs** — `hermes-3`, `hermes-4` (and variants caught by
   `hermes-[0-9]`: `hermes-2`, `deephermes-3`, `hermes-4.3-36b`, …), `nousresearch/...`
   (~140 lines). `hermes_cli/model_switch.py::is_nous_hermes_non_agentic()` depends
   on the literal string; corrupting it breaks model resolution + the non-agentic guard.
3. **`nousresearch.com` doc URLs** (390 files) and the **MIT license author "Nous
   Research"** (`LICENSE`, `pyproject.toml`/`apps/desktop/package.json` author fields —
   legal attribution).
4. **`NOUS_*` environment-variable prefix** (~40 vars: `NOUS_API_KEY`, `NOUS_CLIENT_ID`,
   `NOUS_PORTAL_URL`, `NOUS_INFERENCE_URL`, `NOUS_SCOPE`, …). This is the Nous
   provider's config namespace — distinct from our `HERMES_*` (D2). Never rename it.
5. **Live Nous service endpoints** — hardcoded hosts that are functional API/billing
   infra, not links: `inference-api.nousresearch.com` (`_NOUS_DEFAULT_BASE_URL` in
   `agent/auxiliary_client.py`, `agent/usage_pricing.py`), `portal.nousresearch.com`
   (`DEFAULT_NOUS_PORTAL_URL` in `hermes_cli/auth.py`), plus `inference.nousresearch.com`,
   `chat.nousresearch.com`, `firecrawl-gateway.nousresearch.com`. **Trap:** the
   `hermes` token inside `hermes-agent.nousresearch.com` (266 refs),
   `setup.hermes-agent.nousresearch.com`, and `docs-hermes--agent.nousresearch.com`
   is **upstream infra, not our brand** — a Tier-1/2 "Hermes→ViloForge" replace must
   not rewrite it. *(Replacing these endpoints with our own is a deliberate
   infra/product decision under ADR-0002's leash phase — not a rebrand find/replace.)*
6. **Nous auth-protocol identifiers** — the OAuth `NOUS_CLIENT_ID` and its hardcoded
   client-id GUIDs (e.g. `9d1c250a-e61b-44d9-88ed-5944d1962f5e`), `NOUS_SCOPE` /
   invoke scopes, and the **`x-nous-credits-*` HTTP response headers** (the wire
   contract with Nous's billing API). Renaming any breaks OAuth or credit parsing.
7. **Sibling Nous project names** — `psyche`, `atropos` (Nous Research projects, not
   generic English, not ours; e.g. `github.com/NousResearch/atropos`).
8. **Upstream contacts & community** — `@nousresearch.com` emails (esp.
   `security@nousresearch.com` — the disclosure address must not be rebranded to
   imply *we* handle Nous's reports), `discord.gg/nousresearch`, `github.com/NousResearch/*`.

- **Exclusion patterns** for any sed/codemod: `hermes-[0-9]`, `nous[-_/]hermes`,
  `nousresearch`, `plugins/*/nous/**`, **`NOUS_[A-Z]`**, **`x-nous-`**, **`psyche`**,
  **`atropos`**.

### D5 — Flagged legal special-case (not do-not-touch; requires deliberate change)
`apps/desktop/package.json` declares `"legalTrademarks": "Hermes"`. We must **change
it to the ViloForge mark or clear it** — the rebrand must not ship a desktop app that
continues to claim "Hermes" as a trademark. Handle in Tier 2; called out here because
it is a legal field, not cosmetic.

## Consequences

- **+** Every rebrand edit has a citable contract; "violates ADR-0003 D4" is a
  concrete gate, not vibes.
- **+** Tier ordering front-loads low-risk work and isolates the real
  product-identity decisions (Tier 2) for deliberate review.
- **+** D2 protects all deployed users; D4 protects provider auth + the license.
- **−** The `hermes` command and `HERMES_*` prefix linger as deprecated aliases —
  carrying-cost until a future hard-cut ADR retires them.
- **Neutral:** Tier 3 deferral is inherited from ADR-0002, not an independent choice
  here; it lifts if/when ADR-0002's cut trigger fires.

## Alternatives Considered

- **Single blanket `s/hermes/viloforge/`** — rejected: corrupts model IDs, breaks
  provider auth, violates the license (D4). The four-tier split exists precisely to
  make this impossible to do by accident.
- **Hard-cut the `hermes` command / `HERMES_*` prefix now** — rejected (D2): breaks
  every existing deployment for cosmetic purity.
- **Rename `hermes_cli` in this effort** — rejected (D3 Tier 3 / ADR-0002): ~4,336
  import-site churn for zero user-visible benefit, and it would break the leash-phase
  alignment that keeps upstream security fixes reimplementable.
