# Upstream-watch ledger

The living record required by [ADR-0002](../adr/ADR-0002-upstream-relationship-and-divergence-strategy.md)
(the leash phase). Tracks what we've studied/reimplemented from upstream, security
items, and where the point-5 cut trigger is evaluated each cadence.

- **Upstream:** `NousResearch/hermes-agent` (remote `upstream`,
  `https://github.com/NousResearch/hermes-agent.git`)
- **Our fork:** `ViloForge/hermes-agent` (`origin`)
- **Review cadence:** monthly (and before each rebrand tier)

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
| _pending first sync_ | — | — | — | — | leash on (rebrand not started) |

## Pending action

- **Sync-to-HEAD (ADR-0002 Decision point 4)** — the one-time pre-rebrand sync to
  current upstream. After it lands: **re-run rebrand blast-radius analysis and
  regenerate the knowledge graph** (both were computed at the stale base `bc5ae3919`
  and are invalidated by the sync).
