#!/usr/bin/env bash
#
# preview-smoke.sh — exhaustive smoke / scenario tests for the ViloForge preview.
#
# Drives a *running* preview build (the `viloforge-agent` Docker image served by
# ./preview.sh) the way a real user would — CLI commands, agent chat with tool
# use, dashboard API — and asserts BOTH that it works AND that the rebrand is
# consistent (ViloForge display everywhere; the Tier-3 `hermes`/`HERMES_*`/
# `X-Hermes-*` skeleton intentionally preserved).
#
# WHY THIS EXISTS: so we never hand-invent these checks again. Re-run it after any
# rebrand slice, dependency bump, or release-candidate build to confirm the
# product still works end-to-end and still reads as ViloForge.
#
# ── Prerequisites ───────────────────────────────────────────────────────────
#   1. Docker running.
#   2. The preview up:   ./preview.sh start --build     (builds from your tree)
#      (or `./preview.sh start` to pull the published image).
#   3. At least one model-provider credential auto-detected by preview.sh
#      (DeepSeek via $DEEPSEEK_API_KEY, and/or Claude via ~/.claude). Provider
#      scenarios auto-SKIP when their credential is absent — never fail.
#
# ── Usage ───────────────────────────────────────────────────────────────────
#   docs/viloforge/smoke/preview-smoke.sh              # all phases
#   docs/viloforge/smoke/preview-smoke.sh --quick      # skip the slow Claude/tool scenarios
#   CONTAINER=viloforge-preview DASH=http://localhost:9119 \
#       docs/viloforge/smoke/preview-smoke.sh          # override defaults
#
# Exit code 0 = all run scenarios passed; non-zero = at least one failed.
# (Skipped scenarios do not fail the run.)
#
# Models are pinned as variables below — update them when the default catalog moves.

set -uo pipefail

CONTAINER="${CONTAINER:-viloforge-preview}"
DASH="${DASH:-http://localhost:9119}"
DEEPSEEK_MODEL="${DEEPSEEK_MODEL:-deepseek-chat}"
CLAUDE_MODEL="${CLAUDE_MODEL:-claude-sonnet-4-6}"
QUICK=0; [ "${1:-}" = "--quick" ] && QUICK=1

PASS=0; FAIL=0; SKIP=0; FAILED=()

c_g(){ printf '\033[32m%s\033[0m' "$1"; }
c_r(){ printf '\033[31m%s\033[0m' "$1"; }
c_y(){ printf '\033[33m%s\033[0m' "$1"; }
phase(){ printf '\n\033[1m== %s ==\033[0m\n' "$1"; }
ok(){   PASS=$((PASS+1)); printf '  %s %s\n' "$(c_g ✓)" "$1"; }
bad(){  FAIL=$((FAIL+1)); FAILED+=("$1"); printf '  %s %s\n      %s\n' "$(c_r ✗)" "$1" "${2:-}"; }
skip(){ SKIP=$((SKIP+1)); printf '  %s %s — %s\n' "$(c_y ⊘)" "$1" "${2:-skipped}"; }

# assert a substring IS present in actual output
want(){ local name="$1" expect="$2" actual="$3"
  if printf '%s' "$actual" | grep -qF -- "$expect"; then ok "$name"
  else bad "$name" "expected substring: '$expect' | got: $(printf '%s' "$actual" | tr '\n' ' ' | cut -c1-220)"; fi; }
# assert a substring is ABSENT
deny(){ local name="$1" forbid="$2" actual="$3"
  if printf '%s' "$actual" | grep -qF -- "$forbid"; then bad "$name" "forbidden substring present: '$forbid'"
  else ok "$name"; fi; }

dexec(){ timeout "${1}" docker exec "$CONTAINER" "${@:2}" 2>&1; }    # dexec <timeout> <cmd...>

# ── Preconditions ────────────────────────────────────────────────────────────
phase "Preconditions"
if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$CONTAINER"; then
  printf '  %s preview container %s is not running.\n     Start it:  ./preview.sh start --build\n' "$(c_r ✗)" "$CONTAINER"; exit 2
fi
ok "preview container '$CONTAINER' is running"
TOKEN="$(curl -fsS "$DASH/" 2>/dev/null | grep -oE '__HERMES_SESSION_TOKEN__="[^"]*"' | sed -E 's/.*="([^"]*)"/\1/')"
HAS_DEEPSEEK=0; dexec 15 sh -lc '[ -n "$DEEPSEEK_API_KEY" ] || [ -n "$DEEPSEEK_TOKEN" ]' >/dev/null 2>&1 && HAS_DEEPSEEK=1
HAS_CLAUDE=0;  dexec 15 sh -lc '[ -n "$CLAUDE_CODE_OAUTH_TOKEN" ] || [ -n "$ANTHROPIC_API_KEY" ]' >/dev/null 2>&1 && HAS_CLAUDE=1
[ "$HAS_DEEPSEEK" = 1 ] && ok "DeepSeek credential present" || skip "DeepSeek credential" "unset → provider scenarios skipped"
[ "$HAS_CLAUDE" = 1 ]   && ok "Claude credential present"   || skip "Claude credential" "unset → provider scenarios skipped"

# ── Phase 1: Identity / branding ─────────────────────────────────────────────
phase "1. Identity & branding"
root="$(curl -fsS "$DASH/" 2>/dev/null)"
want "dashboard served — title is ViloForge" "<title>ViloForge Agent - Dashboard</title>" "$root"
want "viloforge --version self-IDs as ViloForge" "ViloForge Agent" "$(dexec 30 viloforge --version)"
want "hermes --version (deprecated alias) still works" "ViloForge Agent" "$(dexec 30 hermes --version)"
# Finding-fix (Tier-2e): argparse prog reflects the invoked command.
want "viloforge --help shows 'usage: viloforge'" "usage: viloforge" "$(dexec 20 viloforge --help)"
want "hermes --help shows 'usage: hermes'"       "usage: hermes"    "$(dexec 20 hermes --help)"

# ── Phase 2: Provider chat E2E + tool use ────────────────────────────────────
# Assertion design: never assert an LLM's *computation* (flaky — models miscompute
# and rephrase). Use deterministic instruction-following ("reply with exactly X")
# to prove the provider responds, and a separate tool-use round-trip with a
# verifiable output. Identity (self-ID as ViloForge) is checked on a NORMAL
# provider (DeepSeek): the Claude Code *OAuth subscription* path intentionally
# self-IDs as "Claude Code" (Anthropic's OAuth requirement, preserved by the
# anthropic_adapter sanitizer in #24) — so we only assert that path *responds*.
phase "2. Provider chat + tools (end-to-end)"
if [ "$HAS_DEEPSEEK" = 1 ]; then
  want "DeepSeek — responds (deterministic echo)" "SMOKE-OK" \
    "$(dexec 120 viloforge -z 'Reply with exactly this token and nothing else: SMOKE-OK' -m "$DEEPSEEK_MODEL" --provider deepseek)"
  want "DeepSeek — agent self-IDs as ViloForge (system-prompt identity)" "ViloForge" \
    "$(dexec 120 viloforge -z 'In one short sentence, what is your product name?' -m "$DEEPSEEK_MODEL" --provider deepseek)"
  if [ "$QUICK" = 0 ]; then
    want "DeepSeek — terminal tool round-trip" "viloforge-smoke-22" \
      "$(dexec 180 viloforge -z 'Use the terminal tool to run exactly: echo viloforge-smoke-$((20+2)) — then report the exact stdout, nothing else.' -m "$DEEPSEEK_MODEL" --provider deepseek)"
  else skip "DeepSeek — terminal tool round-trip" "--quick"; fi
else skip "DeepSeek scenarios" "no credential"; fi
if [ "$HAS_CLAUDE" = 1 ] && [ "$QUICK" = 0 ]; then
  # Claude Code OAuth path: assert it RESPONDS (works), not its identity.
  want "Claude (OAuth subscription path) — responds (deterministic echo)" "SMOKE-OK" \
    "$(dexec 200 viloforge -z 'Reply with exactly this token and nothing else: SMOKE-OK' -m "$CLAUDE_MODEL" --provider anthropic)"
elif [ "$HAS_CLAUDE" != 1 ]; then skip "Claude scenario" "no credential"
else skip "Claude scenario" "--quick"; fi

# ── Phase 3: CLI subcommands (as a user) ─────────────────────────────────────
phase "3. CLI subcommands"
want "viloforge status — ViloForge banner"      "ViloForge Agent Status" "$(dexec 60 viloforge status)"
want "viloforge doctor — ViloForge banner"      "ViloForge Doctor"       "$(dexec 60 viloforge doctor)"
want "viloforge config show — ViloForge banner" "ViloForge Configuration" "$(dexec 40 viloforge config show)"
want "viloforge tools list — toolsets render"   "terminal"               "$(dexec 60 viloforge tools list)"
want "viloforge skills list — table renders"    "Installed Skills"       "$(dexec 60 viloforge skills list)"
want "viloforge sessions list — runs"           "Last Active"            "$(dexec 60 viloforge sessions list)"

# ── Phase 4: Dashboard API + rebrand consistency ─────────────────────────────
phase "4. Dashboard API & rebrand consistency"
if [ -n "$TOKEN" ]; then
  H=(-H "X-Hermes-Session-Token: $TOKEN")
  want "GET /api/status — reports a version" '"version"' "$(curl -fsS "${H[@]}" "$DASH/api/status")"
  plat="$(curl -fsS "${H[@]}" "$DASH/api/messaging/platforms")"
  want "GET /api/messaging/platforms — ViloForge onboarding copy" "ViloForge" "$plat"
  deny "  …and no display 'Hermes Agent' leak in onboarding"      "Hermes Agent" "$plat"
else skip "authed API scenarios" "no session token from dashboard"; fi
# Served JS bundle: no CAPITAL 'Hermes ' display token (skeleton X-Hermes/HERMES_ excluded).
JS_PATH="$(printf '%s' "$root" | grep -oE '/assets/[^"]+\.js' | head -1)"
if [ -n "$JS_PATH" ]; then
  leak="$(curl -fsS "$DASH$JS_PATH" 2>/dev/null | grep -oE '\bHermes [A-Za-z]' | grep -vE 'Hermes Session' | sort -u | head)"
  if [ -z "$leak" ]; then ok "served JS bundle — no capital-'Hermes' display leak"
  else bad "served JS bundle display leak" "$leak"; fi
else skip "served JS bundle scan" "no /assets/*.js found"; fi
# Skeleton MUST be preserved (Tier-3 / wire contract).
want "skeleton preserved — __HERMES_* JS globals" "HERMES_" "$root"
[ -n "$TOKEN" ] && ok "skeleton preserved — X-Hermes-Session-Token accepted by API" || true

# ── Summary ──────────────────────────────────────────────────────────────────
phase "Summary"
printf '  passed: %s   failed: %s   skipped: %s\n' "$(c_g $PASS)" "$([ $FAIL -gt 0 ] && c_r $FAIL || echo 0)" "$(c_y $SKIP)"
if [ "$FAIL" -gt 0 ]; then printf '  failing: %s\n' "${FAILED[*]}"; exit 1; fi
printf '  %s all run scenarios passed\n' "$(c_g ✓)"; exit 0
