# Graphify — the standing code-graph for the ViloForge fork

We adopt **[graphify](https://github.com/safishamsi/graphify)** (`graphifyy`, MIT) as
the on-demand knowledge graph for architecture/blast-radius/scoping work — replacing
the stale one-off `.understand-anything/knowledge-graph.json` dump (generated at an old
commit, never refreshed).

**Why:** an empirical test on this repo ([`knowledge-graph-vs-grep.md`](./knowledge-graph-vs-grep.md))
showed a graph cleanly separates the product's display **surfaces** into communities —
exactly what the Tier-1 rebrand needed when it silently dropped `ui-tui/`. graphify is
the maintained, packaged version of the same idea, with `query` / `path` / `explain` /
`affected` (reverse blast-radius), an MCP server, and incremental `watch`/`update`.

It does **not** replace the token tools. A graph finds *surfaces*; `completeness.py`
finds *tokens*; a live preview catches *rendered art*. Use all three.

## Adoption shape (decisions)

- **On-demand CLI, regenerate-on-demand.** The graph output (`graphify-out/`) is
  **git-ignored**, not committed — committing a multi-MB generated artifact is exactly
  the staleness problem we're leaving behind. Rebuild it when you need it (seconds, no
  LLM for the structural graph).
- **No auto-installed hook (opt-in).** We do **not** run `graphify install` (which would
  write a section + a `PreToolUse` hook into `CLAUDE.md` and change agent behavior on
  every tool call). If you want that, it's your opt-in — see *Optional* below.
- **Pinned** per the dependency policy: `graphifyy>=0.8.49,<0.9`.

## Install (isolated)

```bash
pipx install "graphifyy>=0.8.49,<0.9"          # recommended (isolated tool)
# or a throwaway venv:
python3 -m venv ~/.graphify-venv && ~/.graphify-venv/bin/pip install "graphifyy>=0.8.49,<0.9"
```

For the LLM steps (semantic concepts on prose + community **naming**) with an
OpenAI-compatible backend such as DeepSeek, also install the extra:
`pipx inject graphifyy "graphifyy[openai]"` (or `pip install openai`).

## Build the graph

```bash
cd ~/KB/hermes-agent

# structural graph — Tree-sitter AST + inferred edges. No LLM, no cost, ~seconds.
graphify update .                       # writes ./graphify-out/{graph.json,GRAPH_REPORT.md}

# or a single surface (faster, focused):
graphify update ui-tui                  # writes ui-tui/graphify-out/

# full semantic pass (LLM, uses your configured key — DeepSeek is cheap):
graphify extract . --backend deepseek   # AST + semantic + community names
```

`graphify-out/` is git-ignored. The `GRAPH_REPORT.md` is the human-readable view —
**Community Hubs**, **God Nodes**, **Surprising Connections**.

## Use it (rebrand scoping + general)

```bash
# enumerate display surfaces before scoping a rebrand tier (the Tier-1 miss):
graphify query "display and branding surfaces" --graph graphify-out/graph.json

# reverse blast-radius — what depends on a symbol (sequencing, safe renames):
graphify affected "BRAND" --graph graphify-out/graph.json

# shortest path / plain-language explanation of a node + neighbours:
graphify path "ThemeSwitcher" "web_server" --graph graphify-out/graph.json
graphify explain "applySkin" --graph graphify-out/graph.json
```

**Rebrand workflow:** enumerate surfaces from the graph (`query` / the report's hubs) →
that union with `completeness.py --list` is the work-list → rebrand via
`rebrand_apply` → `diff_gate` (no corruption) + `completeness` (nothing missed) →
live-preview verify. (`docs/viloforge/rebrand/`.)

## Optional: editor/agent integration

graphify can wire itself into assistants, but this changes behavior, so it's opt-in:

```bash
graphify install --platform claude      # writes a CLAUDE.md section + PreToolUse hook
graphify hook install                   # git post-commit/post-checkout: refresh the graph
graphify serve                          # MCP server (query the graph as a tool)
graphify uninstall --purge              # undo + delete graphify-out/
```

Evaluate against the existing `~/KB` Claude Code hooks before installing the
`PreToolUse` hook — don't let it conflict with the KB-scoped governance hooks.
