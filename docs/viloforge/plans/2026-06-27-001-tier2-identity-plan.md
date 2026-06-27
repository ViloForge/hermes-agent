# Tier-2 — Package / CLI / Docker / CI identity (execution sub-plan)

- **Status:** Draft (for review — not yet ratified, no edits applied)
- **Date:** 2026-06-27
- **Governs:** the Tier-2 slice of the rebrand.
- **Permanent context (read first):**
  [ADR-0003](../../adr/ADR-0003-rebrand-identity-and-tiering.md) **D1, D2, D3-Tier-2, D5**
  (D4 = do-not-touch boundary) and
  [ADR-0002](../../adr/ADR-0002-upstream-relationship-and-divergence-strategy.md)
  (the leash → Tier-3 deferral). Tier-1d display rebrand is **complete**
  (PR #21–#32; repo-wide `completeness --max 0` is now a hard CI gate).

---

## 1. What Tier-2 is (and is not)

Tier-1d renamed the **display brand** (cosmetic `\bHermes\b` in prose/chrome).
Tier-2 renames the **structural product identity** — the names the ecosystem
uses to *install, invoke, and ship* the product. Per ADR-0003 D3 it is
**medium risk**: it touches packaging, CLI entrypoints, Docker, and CI — a
break stops *building/shipping*, not just *rendering*.

**In scope (D1 + D3-Tier-2 + D5):** PyPI/package name, the console command,
npm package names, the Docker image, the CI publish + smoke-test plumbing,
and the desktop `legalTrademarks` field.

**Explicitly NOT in scope:**
- **Tier-3 (DEFERRED, ADR-0002 leash):** the `hermes_cli` Python namespace
  (~4,336 import sites), the `HERMES_*` env prefix (~491 vars), `~/.hermes`,
  `X-Hermes-*` headers, the lowercase `hermes` *import* modules. Kept aligned
  with upstream.
- **Tier-4 / D4 do-not-touch:** Nous provider/auth, model IDs, `nousresearch.com`,
  `NOUS_*`, `x-nous-*`, the MIT author "Nous Research", live Nous endpoints,
  `psyche`/`atropos`, the `hermes-agent.nousresearch.com` upstream-infra trap.

**Backward-compat invariant (D2):** the old `hermes` command and the entire
`HERMES_*` prefix are kept as **deprecated aliases (dual-read, warn) for ≥1
release**. Tier-2 is **additive** (`viloforge` *alongside* `hermes`), never a
hard cut.

---

## 2. Verified inventory (current state → target)

Counts/values verified against the tree on `main` (commit at draft time
`c58b1a323`), not from the dated ADR.

### A. Python packaging — `pyproject.toml`
| Line | Current | Target |
| --- | --- | --- |
| `name = "hermes-agent"` | hermes-agent | `viloforge-agent` |
| `[project.scripts]` `hermes = "hermes_cli.main:main"` | hermes | **add** `viloforge = "hermes_cli.main:main"`; **keep** `hermes` (alias, D2) |
| `hermes-agent = "run_agent:main"` | hermes-agent | DECISION D-1 (add `viloforge-agent`? keep only?) |
| `hermes-acp = "acp_adapter.entry:main"` | hermes-acp | DECISION D-1 (add `viloforge-acp`? keep only?) |
| Self-referential extras in `all`/`dashboard`: `"hermes-agent[cron]"`, `[cli]`, `[pty]`, … (~20 refs) | hermes-agent[...] | `viloforge-agent[...]` — **must track the package rename** or `pip install viloforge-agent[all]` resolves a non-existent dist |
| `authors = [{ name = "Nous Research" }]` | Nous Research | **KEEP** (D4 legal attribution) |
| `py-modules = [...]`, target-version, `[tool.*]` | (module names) | **KEEP** (Tier-3 modules) |

> The package is **not published to PyPI** (operator decision — GHCR image
> only), so this rename is *identity metadata* (wheel/sdist `Name:`), not a
> published-install path. Real install is via `scripts/install.sh`.

### B. PyPI publish workflow — `.github/workflows/upload_to_pypi.yml`
- Triggers on `push: tags: ['v20*']` + `workflow_dispatch`; publishes to
  `environment: pypi → https://pypi.org/p/hermes-agent` via OIDC trusted
  publishing (`id-token: write`).
- **No `if: github.repository == …` gate** → a `v20*` tag pushed on the fork
  *would* trigger it (it would fail OIDC, but it is live).
- **Target:** NEUTRALIZE per operator decision (no PyPI publishing). Recommended:
  add `if: github.repository == 'NousResearch/hermes-agent'` to the publish jobs
  (mirrors `docker-publish.yml`, keeps it reimplementable per ADR-0002). The
  `pypi.org/p/hermes-agent` URL is then upstream's and harmless.

### C. npm packages (all `private: true`, none published)
| package.json | name | imported-as / cross-refs |
| --- | --- | --- |
| `package.json` (root) | `hermes-agent` | workspace root |
| `apps/desktop/package.json` | `hermes` | — |
| `apps/bootstrap-installer/package.json` | `@hermes/bootstrap-installer` | — |
| `apps/shared/package.json` | `@hermes/shared` | **imported** by `apps/desktop` (`from '@hermes/shared'`, tsconfig path, `file:../shared` dep) |
| `ui-tui/package.json` | `hermes-tui` | depends on `@hermes/ink` |
| `ui-tui/packages/hermes-ink/package.json` | `@hermes/ink` | **imported across ui-tui** (many `from '@hermes/ink'` + tsconfig path) |
| `web/package.json` | `web` | not branded (no change) |

> **The `@hermes/*` scoped packages are internal module scopes with
> import-edge churn** (every `from '@hermes/ink'` / `'@hermes/shared'` + tsconfig
> path mappings + the `hermes-ink` directory name). This is structurally
> analogous to the `hermes_cli` namespace that Tier-3 **defers**. See DECISION D-2.

### D. Docker
| File | Current | Target |
| --- | --- | --- |
| `docker-compose.yml` (×2 `image:`) | `hermes-agent` | `viloforge-agent` (local image tag) |
| `.github/workflows/viloforge-publish.yml` | `IMAGE: ghcr.io/viloforge/hermes-agent` | `ghcr.io/viloforge/viloforge-agent` |
| `docker-compose.preview.yml` | `ghcr.io/viloforge/hermes-agent:preview` | tracks the GHCR rename |
| `Dockerfile` | comment "Link hermes-agent itself" + `hermes_cli` build steps | comment only; **keep** the `hermes_cli`/module build steps (Tier-3) |
| `docker-compose.windows.yml` (×2) | `nousresearch/hermes-agent:latest` (UPSTREAM Docker Hub) | DECISION D-3 (redirect to our GHCR image?) |
| `docker-publish.yml` | `IMAGE_NAME: nousresearch/hermes-agent`, gated `if: repo == NousResearch/hermes-agent` | **KEEP** (upstream-only, inert on fork) |

### E. CI smoke-test action — `.github/actions/hermes-smoke-test/`
- Directory path `hermes-smoke-test`; `action.yml` already display-renamed
  ("ViloForge smoke test") in Tier-1d. Consumed by `viloforge-publish.yml`
  **and** `docker-publish.yml` (`uses: ./.github/actions/hermes-smoke-test`).
- This is an internal CI path identifier (rename → update both consumers). See
  DECISION D-2 (same internal-churn class as the npm scopes).

### F. D5 — desktop `legalTrademarks`
- `apps/desktop/package.json:226` is **already** `"legalTrademarks": "ViloForge"`
  — swept in by the Tier-1d Desktop slice (#30). **D5 is DONE** (verify only).

### G. Distribution / docs install references (mostly DELIBERATE-INFRA, see D-3)
- `scripts/install.sh`: clones `REPO_URL_{SSH,HTTPS} = …NousResearch/hermes-agent.git`;
  links command at `/usr/local/bin/hermes`; install dir `~/.hermes/hermes-agent`
  & `/usr/local/lib/hermes-agent`; banner URL `hermes-agent.nousresearch.com`
  (D4 trap — keep).
- `website/docs/**`, `website/static/llms-full.txt`: `pip install
  git+https://github.com/NousResearch/hermes-agent.git`, `docker pull
  nousresearch/hermes-agent`.

---

## 3. Decisions — LOCKED (recommended path; operator delegated autonomous execution 2026-06-27)

These were genuine forks. The operator delegated autonomous execution against
the recommended answers; they are now the **baseline of record**. A decision
proving wrong mid-execution counts as an **unforeseen issue → halt & surface**
(see §4 anti-sidetrack rule). Any of these may be vetoed before a slice starts.

- **D-1 — LOCKED: add `viloforge` aliases, keep all olds.** Add `viloforge`
  (primary), `viloforge-agent`, `viloforge-acp` console scripts; keep `hermes` /
  `hermes-agent` / `hermes-acp` as D2 aliases (all point to the same entrypoints).

- **D-2 — LOCKED: rename identity-facing npm names; DEFER the import-heavy
  internal scopes.** Rename `apps/desktop` `name: hermes → viloforge`,
  `@hermes/bootstrap-installer → @viloforge/bootstrap-installer`, root
  `hermes-agent → viloforge-agent` (these have **no** in-source import sites).
  **DEFER** `@hermes/ink`, `@hermes/shared`, `hermes-tui`, the `hermes-ink`
  directory, and `.github/actions/hermes-smoke-test` — they have import-edge /
  path churn and are private/unpublished, so they ride the same ADR-0002 leash
  rationale as `hermes_cli` (revisit with Tier-3). Recorded as a deliberate split
  from ADR-0003's "8 npm names".

- **D-3 — LOCKED: redirect fork-owned infra; docs pass; keep the D4 trap host.**
  Redirect (a) `scripts/install.sh` clone URL `NousResearch/hermes-agent →
  ViloForge/hermes-agent`; (b) `docker-compose.windows.yml`
  `nousresearch/hermes-agent:latest →` our GHCR image; (c) docs install commands
  → fork repo/image. Each is a deliberate, surgical edit (never the brand
  codemod, which excludes `nousresearch`). **KEEP** the
  `hermes-agent.nousresearch.com` banner URL (D4 trap) and upstream-gated
  workflows.

- **D-4 — LOCKED: DEFER install-layout rename.** `~/.hermes/hermes-agent` and
  `/usr/local/lib/hermes-agent` stay (under the Tier-3 `~/.hermes` home; renaming
  breaks in-place upgrades). Revisit with Tier-3.

---

## 4. Execution runbook — autonomous, step-by-step

**Position in the master roadmap:** Tier-1d ✅ done → **Tier-2 (this) ▶ active** →
Tier-3 deferred (ADR-0002). Four execution slices (2a→2d), each its own
branch+PR+green-CI+review+squash-merge, same cadence as Tier-1d. **D5 already
done (#30)** — verify only. The smoke-test action + import-heavy npm scopes are
**deferred** per D-2 (not a slice here).

**Anti-sidetrack rule (autonomous):** follow the steps in order; do not detour
into Tier-3, unrelated cleanups, or anything outside a step's stated edits.
**HALT and surface only on an unforeseen issue:** a step's verification fails in
a way the step doesn't anticipate; a locked decision (D-1…D-4) proves wrong; an
edit would touch the D4 do-not-touch boundary or a Tier-3 token; or CI red that
isn't a known flake. Otherwise proceed slice→slice without stopping.

**Per-slice loop (applies to every slice):** branch off fresh `main` → capture
baseline of the slice's verification scope → make ONLY the listed edits → run the
slice's verification → `diff_gate` + `rebrand-guard` (display) must stay green →
commit (no AI trailer) → push → PR `--repo ViloForge/hermes-agent` → monitor CI
(`rerun --failed` for known flakes; never admin-merge past red) → review (0
corruption sigs, no Tier-3/D4 token disturbed) → squash-merge + delete branch →
kb journal. No `git stash` mid-staging.

### Slice 2a — Python identity + PyPI neutralization
- [ ] 2a.1 Branch `tier2a-python-identity`.
- [ ] 2a.2 Baseline: `scripts/run_tests.sh tests/test_packaging_metadata.py` +
      any console-script/entrypoint tests (grep `tests/` for `project.scripts`,
      `hermes-agent`, `console_scripts`). Record green.
- [ ] 2a.3 `pyproject.toml`: `name = "viloforge-agent"`.
- [ ] 2a.4 `[project.scripts]`: add `viloforge = "hermes_cli.main:main"`,
      `viloforge-agent = "run_agent:main"`, `viloforge-acp = "acp_adapter.entry:main"`;
      KEEP `hermes` / `hermes-agent` / `hermes-acp` (D2 aliases).
- [ ] 2a.5 Update self-referential extras `"hermes-agent[...]"` → `"viloforge-agent[...]"`
      in the `all` + `dashboard` meta-extras (~20 refs). (Doc-comment `pip install
      hermes-agent[...]` lines → viloforge-agent for consistency.)
- [ ] 2a.6 Neutralize `.github/workflows/upload_to_pypi.yml`: add
      `if: github.repository == 'NousResearch/hermes-agent'` to the publish job(s)
      (mirrors `docker-publish.yml`).
- [ ] 2a.7 Verify (clean venv): build (`uv build` / `python -m build`) → wheel +
      sdist `Name:` == `viloforge-agent`; `pip install -e .`; **`viloforge --version`
      AND `hermes --version` both run**; `pip install --dry-run 'viloforge-agent[all]'`
      (or extras resolution check) succeeds. Update `tests/test_packaging_metadata.py`
      to the new name/scripts. Run full `scripts/run_tests.sh` affected scope.
- [ ] 2a.8 Gates (`diff_gate`, `rebrand-guard` display) green; grep-assert no
      `hermes_cli`/`HERMES_*`/`~/.hermes` touched. Commit → PR → CI → merge → kb.

### Slice 2b — Docker image identity
- [ ] 2b.1 Branch `tier2b-docker-identity`.
- [ ] 2b.2 `docker-compose.yml`: `image: hermes-agent` → `viloforge-agent` (×2).
- [ ] 2b.3 `.github/workflows/viloforge-publish.yml`: `IMAGE: ghcr.io/viloforge/hermes-agent`
      → `ghcr.io/viloforge/viloforge-agent`.
- [ ] 2b.4 `docker-compose.preview.yml`: default `PREVIEW_IMAGE` → `…/viloforge-agent:preview`.
- [ ] 2b.5 (D-3b) `docker-compose.windows.yml`: `nousresearch/hermes-agent:latest`
      → `ghcr.io/viloforge/viloforge-agent:latest` (deliberate fork-image redirect).
- [ ] 2b.6 Verify: `docker compose config` resolves; `docker build .` succeeds;
      `./preview.sh stop && ./preview.sh start --build` serves at :9119; live-preview
      checks (title `ViloForge Agent`, `hermes -z` provider round-trip via DeepSeek);
      `actionlint`/CI parses the workflow. Commit → PR → CI → merge → kb. Then
      `./preview.sh stop`.

### Slice 2c — npm identity (identity-facing names only, per D-2)
- [ ] 2c.1 Branch `tier2c-npm-identity`.
- [ ] 2c.2 Rename `name`: `apps/desktop/package.json` `hermes` → `viloforge`;
      `apps/bootstrap-installer/package.json` `@hermes/bootstrap-installer` →
      `@viloforge/bootstrap-installer`; root `package.json` `hermes-agent` →
      `viloforge-agent`.
- [ ] 2c.3 Grep for any reference to those three names (deps, scripts, tauri/electron
      build config, CI) and update in lockstep. **DEFER** `@hermes/ink`,
      `@hermes/shared`, `hermes-tui`, `hermes-ink` dir (D-2).
- [ ] 2c.4 Verify: `npm install` (workspace) resolves; per affected workspace
      `npm run typecheck` + `npm run build` green (network permitting; else CI is the
      net). Commit → PR → CI (typecheck jobs) → merge → kb.

### Slice 2d — Distribution + docs redirects (D-3a/c)
- [ ] 2d.1 Branch `tier2d-distribution-redirects`.
- [ ] 2d.2 `scripts/install.sh`: `REPO_URL_{SSH,HTTPS}` `NousResearch/hermes-agent`
      → `ViloForge/hermes-agent`. KEEP the `hermes-agent.nousresearch.com` banner
      URL (D4 trap) and install dirs `~/.hermes/hermes-agent` (D-4 deferred).
      Ensure the command-link step links **both** `hermes` and `viloforge`.
- [ ] 2d.3 Docs pass: `website/docs/**` + `website/static/llms-full.txt` install
      commands (`git+…/NousResearch/hermes-agent`, `docker pull nousresearch/…`) →
      fork repo / our GHCR image. (Display already Tier-1d-done; this is the infra
      URL/command redirect only.)
- [ ] 2d.4 Verify: `website` docusaurus build succeeds; `bash -n scripts/install.sh`;
      grep-assert no D4 trap host or upstream-gated workflow disturbed. Commit → PR →
      CI → merge → kb.

### Close-out (after 2a–2d merged)
- [ ] Verify D5 (`apps/desktop/package.json` `legalTrademarks` == `ViloForge`).
- [ ] Final check: `viloforge`/`hermes` both work; GHCR image path is
      `…/viloforge-agent`; package identity `viloforge-agent`.
- [ ] kb: mark Tier-2 done; record what remains deferred (D-2 internal scopes,
      D-4 install layout, Tier-3) for the eventual leash-lift.

---

## 5. Verification (per slice — Tier-1d gate doesn't cover Tier-2)

The locked `completeness --max 0` gate is for **display** tokens (`\bHermes\b`)
— it does **not** validate Tier-2 (lowercase identifiers). Tier-2 needs its own
checks:

- **2a:** `pip install -e .` (or build) in a clean venv → wheel/sdist `Name:` is
  `viloforge-agent`; **both** `viloforge --version` and `hermes --version`
  resolve and run; `viloforge-agent[all]` extras resolve; `tests/test_packaging_metadata.py`
  updated + green; full `scripts/run_tests.sh` (entrypoint/console-script tests).
- **2b:** `docker build` succeeds; `docker compose config` resolves the new image;
  `preview.sh --build` serves; `viloforge-publish.yml` validates (dry/dispatch).
- **2c:** `npm install` (workspace) resolves; `npm run typecheck`/`build` per
  workspace (desktop, ui-tui) green — every renamed import resolves.
- **2d:** `viloforge-publish.yml` + `docker-publish.yml` reference the renamed
  action and the workflow parses (actionlint / CI).
- **2e:** docs build (`website` docusaurus build) + manual read of the rendered
  install commands.
- **All:** `diff_gate` clean; `rebrand-guard` (display) still green; no
  `HERMES_*`/`hermes_cli`/`~/.hermes`/`appId`/`scheme`/`Nous` token disturbed
  (grep assertion per slice); **live-preview** for 2b (`preview.sh --build` +
  the `hermes -z` provider round-trip) since the image identity changed.

---

## 6. Risks & gotchas (factual)

- **Self-referential extras** (`hermes-agent[cron]` inside the `all`/`dashboard`
  meta-extras) silently break `viloforge-agent[all]` if not renamed in lockstep
  with the package name.
- **`upload_to_pypi.yml` is ungated** — a CalVer tag push triggers a real
  (failing/unwanted) publish attempt; neutralize *before* any future tag.
- **npm `@hermes/*` import churn** — renaming the scope requires editing every
  `from '@hermes/…'` import + tsconfig `paths` + the `hermes-ink` directory; a
  missed reference is a build break, not a display residual (D-2).
- **Deliberate-infra redirects (D-3)** touch the `nousresearch` token — must be
  surgical, never via the brand codemod (which excludes `nousresearch`), and only
  the fork-owned consumers (install clone URL, our compose), never the D4 trap
  host or upstream-gated workflows.
- **Dual-alias correctness (D2)** — tests must assert BOTH `viloforge` and
  `hermes` resolve; dropping `hermes` is a breaking change we are not making yet.
- **Tier-2 ≠ Tier-3** — do not let `viloforge-agent`/`viloforge` tempt a rename
  of `hermes_cli`/`HERMES_*`/`~/.hermes`; those stay (ADR-0002).

---

## 7. Open product question (separate from Tier-2)

Whether the ViloForge fork should **display upstream Hermes testimonials**
(`website/src/data/userStories.json`, kept verbatim + exempted in Tier-1d) is a
content/product decision, not a rename. Tracked, not part of Tier-2 execution.
