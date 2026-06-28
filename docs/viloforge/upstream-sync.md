# Upstream-watch ledger

The living record required by [ADR-0002](../adr/ADR-0002-upstream-relationship-and-divergence-strategy.md)
(the leash phase). Tracks what we've studied/reimplemented from upstream, security
items, and where the point-5 cut trigger is evaluated each cadence.

- **Upstream:** `NousResearch/hermes-agent` (remote `upstream`,
  `https://github.com/NousResearch/hermes-agent.git`)
- **Our fork:** `ViloForge/hermes-agent` (`origin`)
- **Review cadence:** monthly (and before each rebrand tier)

## Sync procedure

Upstream syncs land on `main` via a **merge commit (`gh pr merge … --merge`), never a
squash** — the decision and its rationale live in the rebrand plan's Pre-flight
(`plans/2026-06-24-001-rebrand-tiered-plan.md`, Pre-flight 3), which is the source of
truth; this section is the operational pointer. In short: a true merge keeps `main` a
descendant of upstream (merge-base advances, security cherry-picks keep accurate
ancestry, the divergence count stays truthful, authorship survives); a squash breaks
all four.

After each sync: record the synced upstream SHA in **Studied-through** below, then
re-run rebrand blast-radius + regenerate the knowledge graph (both go stale at the old
base).

## Divergence snapshot — 2026-06-24 (pre-sync)

| Axis | Value |
| --- | --- |
| Our fork base (merge-base) | `ef4b897a1` — dated **2026-06-18** |
| Upstream HEAD at first fetch | `89540d592` — dated 2026-06-24 |
| **Upstream ahead of us** | **745 commits** (~124/day — very high velocity) |
| Our fork delta (on top) | 3 commits: GHCR publish (#1) + ASDLC governance (#2, #3) |
| Conflict surface for sync | **only `AGENTS.md`** (upstream touched it in 2 commits; we prepended). All other ViloForge files are new → zero collision. We have changed no code. |

> **Correction to record:** earlier framing called this "near-zero divergence / fork
> + 2 commits." That described *our commits on top*; it masked that our **base is 745
> upstream commits stale**. ADR-0002's *decision* (sync-first; conflict-cheap) holds —
> the conflict surface really is ~1 file — but the base was not near-current.

## Studied-through

| Date | Studied through SHA | Reimplemented | Skipped | Security items | Cut-trigger check |
| --- | --- | --- | --- | --- | --- |
| 2026-06-24 | `89540d592` (synced via PR #4, merge commit `be87d31b3`) | — (one-time pre-rebrand sync — adopted upstream HEAD wholesale, nothing to selectively reimplement) | — | none flagged in the synced range | leash on (rebrand not started) |
| 2026-06-28 | `0800f1c28` (reviewed `89540d592..0800f1c28`, **not merged** — selective port) | **Tier-A ported on `sync-sweep`** (9 commits, `cherry-pick -x`, authorship preserved): `85e084d60` email GHSA, `9c6229ce2` cred-safe subprocess env (+`dbbf102b8` prereq), `c15945655` terminal cwd, `fbfccbb3e` cron unicode, `190e1ffac` dotted-key redact, `8ff426e53`+`6c58878e7` browser typed-text redact, `6305ac0e4` MCP OSV preflight. 384 scoped tests green. | product-surface PRs (whatsapp queue, desktop UI, TUI billing, relay product features), test/CI/AUTHOR_MAP chores; **Tier-B backlog deferred** (port on need) | **18 flagged** — see triage below; 1 disclosed advisory (GHSA-rxqh-5572-8m77, email From: spoofing) — **ported** | **leash STAYS ON** — upstream relevance high (see §cut-trigger) |

## Post-sync snapshot — 2026-06-24

| Axis | Value |
| --- | --- |
| Sync landed | PR #4, merge commit `be87d31b3` (merge of branch tip `64fab5f81`, whose 2nd parent is upstream `89540d592`) |
| New merge-base(`main`, `upstream/main`) | `89540d592` (advanced from the stale `ef4b897a1`) |
| Divergence after sync | **12 commits** behind upstream (`upstream/main` moved to `ae20c3fb9` during the work) — accurate because the sync was a true merge |
| CI on PR #4 | 2 red checks, both **false positives for a bulk sync**, ignored deliberately (`main` is not branch-protected): `supply-chain` fired on an upstream commit adding 59 lines to `setup.py` (install-hook heuristic — upstream's own change); `contributor-check` diffs `merge-base..HEAD --no-merges` = all 745 upstream commits, whose authors aren't in our `scripts/release.py` AUTHOR_MAP (a contributor-PR check, meaningless for a sync) |

## Upstream-watch sweep — 2026-06-28 (first post-rebrand cadence)

First monthly cadence after Tier-1d + Tier-2 landed. This is now a **selective
review**, not a sync-to-HEAD: a full merge is no longer the cheap move (our 40 rebrand
commits would conflict across every display/identity surface upstream keeps touching).
Per ADR-0002 point 3 we instead `cherry-pick -x` security fixes into the **un-rebranded**
subsystems (auth, provider adapters, egress/terminal, MCP, redaction, threat-scanning),
which stay merge-clean precisely because we never rebranded them.

### Divergence snapshot — 2026-06-28

| Axis | Value |
| --- | --- |
| merge-base(`main`, `upstream/main`) | `89540d592` (unchanged since the 2026-06-24 sync — we have not merged since) |
| Upstream HEAD | `0800f1c28` — dated **2026-06-28** |
| **Upstream ahead of us** | **557 commits** (the prior ledger's "12" was the 2026-06-24 figure; upstream runs ~124/day) |
| Our delta on top | **40 commits** (all Tier-1d display + Tier-2 identity rebrand work) |
| Conflict surface for a full merge | **no longer ~1 file** — upstream churn now overlaps our rebranded display/package surfaces. Full merge deprecated in favor of selective cherry-pick (above). |

### Security triage — `89540d592..0800f1c28` (557 commits)

Method: subject-line security grep **∪** file-path scan over the un-rebranded
sensitive subsystems (`*auth*`, `*cred*`, `tirith_security`, `*redact*`,
`threat_patterns`, `file_safety`, `proxy/adapters`, `tools/environments`, `mcp*`).
All listed commits touch files **outside** the ADR-0003 D4 do-not-touch boundary →
expected to cherry-pick clean.

**Tier A — port now (disclosed vuln / exploitable; recommended batch):**

| SHA | Fix | Subsystem |
| --- | --- | --- |
| `85e084d60` | **GHSA-rxqh-5572-8m77** — reject spoofed `From:` header for email authz (verify against `Authentication-Results`); fail-closed | `plugins/platforms/email/adapter.py` |
| `9c6229ce2` | centralize credential-safe subprocess env — non-terminal spawn sites (browser, ACP, installers) leaked operator creds via `os.environ.copy()` | `tools/environments/local.py` |
| `c15945655` | sanitize host/relative cwd OVERRIDE before `docker run -w` (override bypassed the container-cwd guard) | terminal tool |
| `fbfccbb3e` | align cron invisible-unicode set with install scanner (prompt-injection bypass via U+2062–2064/2066–2069) | `tools/cronjob_tools.py` |
| `dbbf102b8` | strip `VIRTUAL_ENV`/`CONDA_PREFIX` from terminal subprocess env | terminal env |
| `190e1ffac` | redact passwords in lowercase/dotted config keys | redactor |
| `6c58878e7` + `8ff426e53` | force secret-pattern redaction on `browser_type` typed-text display | browser tool |
| `6305ac0e4` | run MCP OSV malware preflight off the event loop with bounded timeout (supply-chain scan) | MCP |

**Tier B — backlog (security-sensitive robustness/authz; port on need):**

`07cc567df` tirith crash circuit-breaker (DoS hang) · `dbf079733` tirith mkdtemp
temp-dir leak · `88c02469c` MCP breaker wedge on dead transport · `e55ddc3e3` /
`075f93ad7` MCP background-OAuth stdin / stale-client recovery · `72ae16325` /
`d33516483` / `0c3f197cf` relay delivery-authz · `fbf748b28` / `dbe734bef`
dashboard-auth OIDC redirect / non-interactive provider exclusion · `fc70d023d`
Telegram bot-auth policy · `a8c862900` TUI replay-history sanitize on resume ·
`1207d81ee` unify outbound chat redaction · `b34771fc0` prompt_toolkit CPR
escape-sequence leak · credential-pool robustness (`8b4c29f0f` `2af1678bf`
`32732a8f8` `3fe16e3cd` `635841d21` `f0de4c6a4` `5a5396aec` `1dde7e2f2`).

**Skipped (out of leash scope):** product-surface features (whatsapp send-queue,
desktop sidebar/projects, relay multi-platform Phase 1.5, TUI billing), Windows
terminal-popup churn (later reverted upstream), and all `chore(release)` AUTHOR_MAP /
test-only commits.

### Cut-trigger evaluation (ADR-0002 point 5) — **leash STAYS ON**

| Condition | Verdict |
| --- | --- |
| Alignment blocks the product | **No** — no wanted change is currently blocked by skeleton alignment (Tier-3 is deferred for its own reasons, not blocked by a pending product need). |
| Upstream relevance decays | **No** — 18 security items in one cadence incl. a disclosed advisory; the leash is actively paying off. |
| Divergence outgrows the map | **No** — every Tier-A fix lands in an un-rebranded file at the same path as upstream; "read the fix, find the spot" still works. |

→ All three negative ⇒ leash remains the standing policy. Re-evaluate next cadence
(~2026-07-28, or before any future tier).

## Pending action

- **Port Tier-A security batch** — ✅ **done** on branch `sync-sweep` (9 commits incl.
  the `dbbf102b8` prereq; per-task branches `--no-ff`-merged; each scoped-tested; 384
  consolidated tests green). Notable reimplements: `9c6229ce2` needed `dbbf102b8`'s
  `_ACTIVE_VENV_MARKER_VARS` (ported first) and three conflict sites where upstream
  context referenced intermediate-commit symbols our tree lacks (`git_probe`,
  `windows_hide_flags`, the `target`/`constraints` lazy-install machinery) — dropped,
  not blindly taken. Awaiting **HITL review + merge `sync-sweep` → `main`** (T9).
- **Tier-B backlog** (relay authz, dashboard-auth, MCP OAuth, tirith DoS,
  credential-pool robustness) — deferred; port on need at a future cadence.
- **Re-run rebrand blast-radius analysis + regenerate the knowledge graph** — both were
  computed at the stale base `bc5ae3919` and are invalidated by the sync. Do before
  trusting any count or the graph for rebrand sequencing.
