# Knowledge graphs vs. grep — what each catches (rebrand tooling note)

**TL;DR:** A code knowledge graph finds **surfaces and structure**; grep finds **tokens**.
The Tier-1 rebrand misses needed *both*, and we used *neither* systematically — so they
slipped. This note records an empirical test of two graph tools so we pick the right
tool next time. It is the evidence behind the *"Rebrand completeness discipline"*
section in `AGENTS.md` and behind **ADR-0004**'s completeness layer.

## The two tools

| Tool | Status here | What it is |
| --- | --- | --- |
| **understand-anything** | **already in the repo** (`.understand-anything/knowledge-graph.json`, regenerated in PR #8) | Knowledge-graph skill: file/AST structure + summaries + import edges, grouped into architectural **layers**. |
| **graphify** (`graphifyy`, MIT, [github.com/safishamsi/graphify](https://github.com/safishamsi/graphify)) | **evaluated, not installed** | Same category, more packaged: Tree-sitter AST + heuristic *inferred* edges → NetworkX graph + **Leiden communities**, with `query`/`path`/`explain`/`affected` and an MCP server. LLM is used for *prose* concepts and *community naming*, not code edges. |

Both are **node/edge level**. Neither is a string-literal index.

## What was missed in Tier-1 (the test cases)

1. **`ui-tui/` never scoped** — its ASCII banner still read `HERMES-AGENT`; a whole
   display surface was dropped from the hand-listed scope. *(root cause A)*
2. **Backend shadows frontend** — the dashboard theme label `Hermes Teal` is served by
   `hermes_cli/web_server.py`, which shadows the rebranded `web/src/themes/presets.ts`
   (`ViloForge Teal`). *(root cause B)*

## Empirical result (2026-06-25, run on this repo)

Tested with graphify (free AST mode for structure, plus a deep-mode pass on a
theme-only corpus); the conclusions hold for understand-anything too — it models the
same things (it has a dedicated **"Terminal UI"** layer and tags `branding.tsx` as a
`banner`).

| Capability | Graph tool? | Evidence |
| --- | --- | --- |
| **A. Enumerate display surfaces / find an unscoped one** | **✅ yes** | The 5 surfaces separate cleanly into communities (TUI = 100%-pure communities; `ui-tui/banner.ts` + `branding.tsx` co-clustered). The free `GRAPH_REPORT.md` lists banner/brand/theme/skin hubs across CLI **and TUI and** Web — the omitted TUI is right there. 8404 nodes in 13 s, `$0`. |
| **B. Detect a shadowing duplicate across the front/back-end boundary** | **❌ no** | **0** Python↔TS cross-file edges, *even in a corpus of only the theme files*. Graphs link **within-language** structure (imports/calls), not the *same string literal* defined in a Python backend and a TS frontend. "Surprising Connections" were all within-surface. |
| **C. Enumerate which exact tokens remain (the work-list)** | **❌ no** | Node-level: it locates `Banner()`, `BRAND` — never the literal `HERMES-AGENT` / `Hermes Teal`. graphify's own tagline is *"query **instead of** grepping."* |

## The division of labor (use both)

- **Knowledge graph → scope, surfaces, blast-radius.** Derive "what surfaces exist"
  from the graph's layers/communities (catches the *unscoped-surface* class), and use
  reverse-impact (`affected "X"`) for blast-radius/sequencing. This is the existing kb
  guidance: *"use the graph for blast-radius/sequencing reasoning."*
- **grep / a completeness sweep → tokens.** A repo-wide grep of display-brand tokens
  (minus the D4 do-not-touch boundary and the intentional-keep set) is the only thing
  that catches *shadowing duplicates* and produces the residual-token work-list. This
  is **ADR-0004**'s completeness layer, extended from per-slice to a **global** sweep.

**Neither replaces the other, and a graph does not fix a process gap.** The Tier-1
misses happened because the scope was hand-listed and the graph we *already had* wasn't
consulted — not because a graph tool was missing.

## Reproduce

```bash
python3 -m venv /tmp/graphify-venv && /tmp/graphify-venv/bin/pip install graphifyy
# structural graph, no LLM, no cost:
/tmp/graphify-venv/bin/graphify update <corpus>          # AST nodes/edges → graphify-out/
/tmp/graphify-venv/bin/graphify cluster-only <corpus> --no-label --no-viz
# inspect graphify-out/GRAPH_REPORT.md → "Community Hubs", "God Nodes", "Surprising Connections"
# (DeepSeek/OpenAI-compatible community naming needs the extra: pip install "graphifyy[openai]")
```

## Recommendation

1. **At rebrand scoping time, open the graph report** and enumerate the display
   surfaces from it (CLI, TUI, Web, Docs, Desktop) — do not hand-list directories.
2. **Run a global token-completeness sweep** (grep-based) before any tier is "done".
3. **Adopt one maintained graph** as the standing tool. **Adopted: graphify** —
   on-demand, regenerate-on-demand, pinned. Setup + the rebrand-scoping workflow live
   in [`graphify.md`](./graphify.md). (Replaces the stale one-off `.understand-anything`
   dump; the `PreToolUse` hook integration is left opt-in.)
