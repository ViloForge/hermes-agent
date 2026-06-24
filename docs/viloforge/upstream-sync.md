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

## Post-sync snapshot — 2026-06-24

| Axis | Value |
| --- | --- |
| Sync landed | PR #4, merge commit `be87d31b3` (merge of branch tip `64fab5f81`, whose 2nd parent is upstream `89540d592`) |
| New merge-base(`main`, `upstream/main`) | `89540d592` (advanced from the stale `ef4b897a1`) |
| Divergence after sync | **12 commits** behind upstream (`upstream/main` moved to `ae20c3fb9` during the work) — accurate because the sync was a true merge |
| CI on PR #4 | 2 red checks, both **false positives for a bulk sync**, ignored deliberately (`main` is not branch-protected): `supply-chain` fired on an upstream commit adding 59 lines to `setup.py` (install-hook heuristic — upstream's own change); `contributor-check` diffs `merge-base..HEAD --no-merges` = all 745 upstream commits, whose authors aren't in our `scripts/release.py` AUTHOR_MAP (a contributor-PR check, meaningless for a sync) |

## Pending action

- **Sync-to-HEAD (ADR-0002 Decision point 4)** — ✅ done (above). 
- **Re-run rebrand blast-radius analysis + regenerate the knowledge graph** — both were
  computed at the stale base `bc5ae3919` and are invalidated by the sync. Do before
  trusting any count or the graph for rebrand sequencing.
