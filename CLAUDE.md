@AGENTS.md

## Claude Code — ViloForge fork

Claude Code reads `CLAUDE.md`, not `AGENTS.md`, so the line above imports the full
`AGENTS.md` (including the **⚖️ ViloForge fork — ASDLC governance** section at its
top). That governance is binding here — read it before any change.

The short version of the gate (see `AGENTS.md` + `docs/adr/` for the authoritative form):

- **Decisions before code.** Record decision-grade / fork-level choices as an ADR in
  `docs/adr/` (Nygard, immutable) *before* implementing. Cite `Constitutional: yes`
  ADRs by number.
- **Respect the do-not-touch boundary.** Never rebrand the upstream Nous surface
  (Nous Portal provider/auth, `hermes-3/4` model IDs, `nousresearch.com`, MIT author).
- **Keep the skeleton aligned with upstream** (`hermes_cli`, `HERMES_*`) per ADR-0002 —
  do not rename the internal namespace.
- Prefer **plan mode** for rebrand edits; implement one tier at a time, human-gated.
