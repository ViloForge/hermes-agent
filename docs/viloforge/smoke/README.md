# Preview smoke / scenario tests

`preview-smoke.sh` is the **reusable, exhaustive smoke harness** for a running
ViloForge preview build. It drives the served `viloforge-agent` image the way a
real user would and asserts both that the product **works end-to-end** and that
the **rebrand is consistent** (ViloForge display everywhere; the deferred
`hermes` / `HERMES_*` / `X-Hermes-*` skeleton intentionally preserved).

Re-run it after any rebrand slice, dependency bump, or release-candidate build —
so we never hand-invent these checks again.

## Run it

```bash
# 1. Bring the preview up (builds the image from your working tree):
./preview.sh start --build          # or `./preview.sh start` to pull the published image

# 2. Run the harness:
docs/viloforge/smoke/preview-smoke.sh           # all phases
docs/viloforge/smoke/preview-smoke.sh --quick   # skip slow Claude / tool scenarios

# 3. Tear down when done:
./preview.sh stop
```

Exit code `0` = all *run* scenarios passed; non-zero = at least one failed.
Scenarios whose provider credential is missing **auto-skip** (never fail).

## Prerequisites

- Docker running, and the preview container up (`./preview.sh start[ --build]`).
- At least one model-provider credential auto-detected by `preview.sh`
  (DeepSeek via `$DEEPSEEK_API_KEY`, Claude via `~/.claude`). Provider scenarios
  skip cleanly when their credential is absent.

## Overrides (env vars)

| Var | Default | Purpose |
| --- | --- | --- |
| `CONTAINER` | `viloforge-preview` | preview container name |
| `DASH` | `http://localhost:9119` | dashboard base URL |
| `DEEPSEEK_MODEL` | `deepseek-chat` | model id for DeepSeek scenarios |
| `CLAUDE_MODEL` | `claude-sonnet-4-6` | model id for Claude scenarios |

## What it covers (scenario matrix)

| Phase | Scenarios |
| --- | --- |
| **0. Preconditions** | container running; dashboard reachable; which provider creds are present |
| **1. Identity & branding** | dashboard `<title>`; `viloforge --version` + `hermes --version` (D2 alias); `viloforge --help` → `usage: viloforge` and `hermes --help` → `usage: hermes` (Tier-2e dynamic-prog fix) |
| **2. Provider chat + tools (E2E)** | DeepSeek reasoning; DeepSeek terminal-tool round-trip; Claude OAuth answer + self-ID — the real agent loop, not mocks |
| **3. CLI subcommands** | `status` / `doctor` / `config show` ViloForge banners; `tools list`; `skills list`; `sessions list` |
| **4. Dashboard API & consistency** | `/api/status`, `/api/messaging/platforms` render ViloForge with **no** `Hermes Agent` display leak; served JS bundle has **no** capital-`Hermes` display token; the `__HERMES_*` / `X-Hermes-Session-Token` skeleton **is** preserved |

## Design notes / how to extend

- Pure `bash` + `docker exec` + `curl` — no extra deps, mirrors `preview.sh`.
- Helpers: `want NAME EXPECT ACTUAL` (assert substring present),
  `deny NAME FORBID ACTUAL` (assert absent), `skip`, `dexec TIMEOUT CMD…`.
- Add a scenario by calling `want`/`deny` inside the relevant `phase`. Keep
  provider scenarios guarded by `$HAS_DEEPSEEK` / `$HAS_CLAUDE`.
- This harness needs Docker + a live preview + creds, so it is **operator-run**,
  not a hermetic CI unit test. (Behavioral invariants that *can* run hermetically
  belong in `tests/` instead.)
- Lives under `docs/viloforge/` so its embedded `Hermes`/`X-Hermes` check-strings
  are self-exempt from the rebrand completeness gate.
