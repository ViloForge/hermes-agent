#!/usr/bin/env bash
#
# preview.sh — start/stop the ViloForge Agent preview (Tier-1 rebrand) locally.
#
# Quick use:
#   ./preview.sh start       # AUTO-detects creds, PULLS the published image, runs
#   ./preview.sh start --build  # BUILD the image from your working tree first, then run
#                               # (reflects local/uncommitted changes; full multi-stage build, slow)
#   ./preview.sh status      # show what's running + which providers were detected
#   ./preview.sh stop        # stop (keeps the throwaway data volume)
#   ./preview.sh logs        # follow logs
#   ./preview.sh reset       # stop + WIPE the throwaway data volume
#   ./preview.sh seed        # OPTIONAL: store creds explicitly in .preview.env
#
# Credentials are resolved AUTOMATICALLY (no manual step needed), in order:
#   DeepSeek : $DEEPSEEK_API_KEY → $DEEPSEEK_TOKEN → .preview.env → ~/.hermes/.env
#   Claude   : $CLAUDE_CODE_OAUTH_TOKEN → .preview.env → ~/.hermes/.env →
#              the live Claude Code subscription token in ~/.claude/.credentials.json
#              (sk-ant-oat OAuth; note it expires ~hourly, so re-run start to refresh;
#               'claude setup-token' yields a durable token if you prefer).
# Creds are passed to the container as env vars — never written to the image, the
# repo, or the data volume. The data volume is throwaway and isolated from ~/.hermes.
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$REPO_DIR/docker-compose.preview.yml"
SECRETS_FILE="${VILOFORGE_PREVIEW_ENV:-$REPO_DIR/.preview.env}"
URL="http://localhost:9119"
PUBLISHED_IMAGE="ghcr.io/viloforge/hermes-agent:preview"
LOCAL_IMAGE="viloforge-agent:preview-local"   # tag for `--build` (working-tree image)

# ---- docker compose v2 (plugin) with a legacy fallback -------------------------
if docker compose version >/dev/null 2>&1; then
  dc() { docker compose -f "$COMPOSE_FILE" "$@"; }
elif command -v docker-compose >/dev/null 2>&1; then
  dc() { docker-compose -f "$COMPOSE_FILE" "$@"; }
else
  echo "error: need Docker with the Compose plugin (docker compose) or docker-compose." >&2
  exit 1
fi

c_dim() { printf '\033[2m%s\033[0m\n' "$*"; }
c_ok()  { printf '\033[32m%s\033[0m\n' "$*"; }
c_warn(){ printf '\033[33m%s\033[0m\n' "$*"; }

# ---- automatic credential resolution -----------------------------------------
# Per provider, precedence (first hit wins, an already-set env var always wins,
# empty values never clobber): existing env > .preview.env > ~/.hermes/.env >
# auto-detect (DEEPSEEK_TOKEN alias / live Claude Code subscription creds).
DEEPSEEK_SRC=""; CLAUDE_SRC=""

_from_envfile() { # file key  → prints a non-empty value, or returns 1
  [ -r "${1:-}" ] || return 1
  local v; v=$(grep -E "^$2=" "$1" 2>/dev/null | tail -1) || return 1
  v="${v#*=}"; v="${v%\"}"; v="${v#\"}"; v="${v%\'}"; v="${v#\'}"
  [ -n "$v" ] && printf '%s' "$v"
}

_claude_token_from_credentials() { # prints a valid (unexpired) OAuth token, or nothing
  local f="$HOME/.claude/.credentials.json"
  [ -r "$f" ] || return 1
  python3 - "$f" 2>/dev/null <<'PY'
import json, sys, time
try:
    oa = json.load(open(sys.argv[1])).get("claudeAiOauth", {})
    t, e = oa.get("accessToken", ""), oa.get("expiresAt", 0) / 1000.0
    # Anthropic OAuth form (sk-ant-oat / sk-ant-, but not the sk-ant-api key form),
    # and still valid for >60s — the anthropic provider's claude-code path needs this.
    if t.startswith("sk-ant-") and not t.startswith("sk-ant-api") and e > time.time() + 60:
        print(t)
except Exception:
    pass
PY
}

_claude_creds_expiry_h() {
  local f="$HOME/.claude/.credentials.json"
  [ -r "$f" ] || return 1
  python3 - "$f" 2>/dev/null <<'PY'
import json, sys, time
try:
    e = json.load(open(sys.argv[1])).get("claudeAiOauth", {}).get("expiresAt", 0) / 1000.0
    print(f"{(e - time.time()) / 3600:.1f}")
except Exception:
    pass
PY
}

load_secrets() {
  local hermes_env="$HOME/.hermes/.env" v=""

  # DeepSeek
  if   [ -n "${DEEPSEEK_API_KEY:-}" ]; then DEEPSEEK_SRC="env DEEPSEEK_API_KEY"
  elif [ -n "${DEEPSEEK_TOKEN:-}" ]; then DEEPSEEK_API_KEY="$DEEPSEEK_TOKEN"; DEEPSEEK_SRC="env DEEPSEEK_TOKEN"
  elif v=$(_from_envfile "$SECRETS_FILE" DEEPSEEK_API_KEY); then DEEPSEEK_API_KEY="$v"; DEEPSEEK_SRC=".preview.env"
  elif v=$(_from_envfile "$hermes_env" DEEPSEEK_API_KEY);   then DEEPSEEK_API_KEY="$v"; DEEPSEEK_SRC="~/.hermes/.env"
  fi

  # Claude Code subscription
  if   [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then CLAUDE_SRC="env CLAUDE_CODE_OAUTH_TOKEN"
  elif v=$(_from_envfile "$SECRETS_FILE" CLAUDE_CODE_OAUTH_TOKEN); then CLAUDE_CODE_OAUTH_TOKEN="$v"; CLAUDE_SRC=".preview.env"
  elif v=$(_from_envfile "$hermes_env" CLAUDE_CODE_OAUTH_TOKEN);   then CLAUDE_CODE_OAUTH_TOKEN="$v"; CLAUDE_SRC="~/.hermes/.env"
  elif v=$(_claude_token_from_credentials);                        then CLAUDE_CODE_OAUTH_TOKEN="$v"; CLAUDE_SRC="claude-live"
  fi

  # Model: an OPTIONAL pin. Only honor an explicit value (env or .preview.env); do
  # NOT force a default — HERMES_MODEL overrides the dashboard model picker (the
  # tui_gateway reads it and ignores config.yaml), so defaulting it would make the
  # picker a no-op. Unset ⇒ the dashboard picker / config.yaml controls the model.
  if [ -z "${HERMES_MODEL:-}" ]; then v=$(_from_envfile "$SECRETS_FILE" HERMES_MODEL) && HERMES_MODEL="$v" || true; fi

  # Export only non-empty (compose passes these with the bare `- VAR` form, so an
  # unset var is omitted rather than injected empty).
  if [ -n "${DEEPSEEK_API_KEY:-}" ]; then export DEEPSEEK_API_KEY; else unset DEEPSEEK_API_KEY 2>/dev/null || true; fi
  if [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then export CLAUDE_CODE_OAUTH_TOKEN; else unset CLAUDE_CODE_OAUTH_TOKEN 2>/dev/null || true; fi
  if [ -n "${HERMES_MODEL:-}" ]; then export HERMES_MODEL; else unset HERMES_MODEL 2>/dev/null || true; fi
}

provider_summary() {
  local any=0 h
  if [ -n "${DEEPSEEK_API_KEY:-}" ]; then c_ok "  ✓ DeepSeek                 (${DEEPSEEK_SRC})"; any=1; fi
  if [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then
    if [ "$CLAUDE_SRC" = "claude-live" ]; then
      h=$(_claude_creds_expiry_h || true); h="${h:-?}"
      c_ok  "  ✓ Claude Code subscription (~/.claude live token — expires in ${h}h)"
      c_dim "    for a durable token: run 'claude setup-token' then export CLAUDE_CODE_OAUTH_TOKEN"
    else
      c_ok "  ✓ Claude Code subscription (${CLAUDE_SRC})"
    fi
    any=1
  fi
  if [ "$any" = 0 ]; then
    c_warn "  ! no provider creds found — chrome is visible but chat won't work."
    c_dim  "    set DEEPSEEK_API_KEY / run 'claude setup-token' / re-run the launcher with 'seed'"
  fi
  if [ -n "${HERMES_MODEL:-}" ]; then
    c_dim "  model: pinned to ${HERMES_MODEL} (HERMES_MODEL set — overrides the dashboard picker)"
  else
    c_dim "  model: choose in the dashboard's model picker (DeepSeek or a claude-* model)"
  fi
}

cmd_seed() {
  local example="$REPO_DIR/.preview.env.example"
  [ -f "$SECRETS_FILE" ] || { [ -f "$example" ] && cp "$example" "$SECRETS_FILE"; }
  echo "Seeding preview credentials → $SECRETS_FILE (git-ignored)"
  echo

  # DeepSeek
  printf 'DeepSeek API key (https://platform.deepseek.com/, blank = skip): '
  read -rs ds; echo
  # Claude Code subscription token
  if command -v claude >/dev/null 2>&1; then
    c_dim "Claude Code CLI detected — get a long-lived token with:  claude setup-token"
  else
    c_dim "Claude Code token: run 'claude setup-token' on a machine with the Claude Code CLI + subscription."
  fi
  printf 'Claude Code OAuth token (paste, blank = skip): '
  read -rs cc; echo
  printf 'Pin a model? (blank = let the dashboard picker choose) [blank]: '
  read -r mdl

  # Write the file (only overwrite keys the user provided; keep prior values otherwise).
  _set_kv() { # file key value
    local f="$1" k="$2" v="$3"
    [ -z "$v" ] && return 0
    if grep -qE "^${k}=" "$f" 2>/dev/null; then
      # portable in-place edit (no sed -i flavour assumptions)
      grep -vE "^${k}=" "$f" > "$f.tmp" && mv "$f.tmp" "$f"
    fi
    printf '%s=%s\n' "$k" "$v" >> "$f"
  }
  touch "$SECRETS_FILE"; chmod 600 "$SECRETS_FILE"
  _set_kv "$SECRETS_FILE" DEEPSEEK_API_KEY "$ds"
  _set_kv "$SECRETS_FILE" CLAUDE_CODE_OAUTH_TOKEN "$cc"
  # Model pin is optional — only record it if the user gave one (else the picker rules).
  grep -vE '^HERMES_MODEL=' "$SECRETS_FILE" > "$SECRETS_FILE.tmp" 2>/dev/null && mv "$SECRETS_FILE.tmp" "$SECRETS_FILE" || true
  [ -n "$mdl" ] && printf 'HERMES_MODEL=%s\n' "$mdl" >> "$SECRETS_FILE"

  # Lock down perms LAST — the grep>tmp>mv rewrites above recreate the file with
  # the default umask (644), so chmod must come after every write.
  chmod 600 "$SECRETS_FILE"
  echo; c_ok "Saved. Now run 'start'."
}

cmd_start() {
  local build=0 a
  for a in "$@"; do [ "$a" = "--build" ] && build=1; done
  load_secrets
  if [ "$build" = 1 ]; then
    # Build from the working tree and point compose at that image (overrides the
    # default published image via VILOFORGE_PREVIEW_IMAGE in docker-compose.preview.yml).
    export VILOFORGE_PREVIEW_IMAGE="$LOCAL_IMAGE"
    echo "Building the preview image from your working tree → $LOCAL_IMAGE"
    c_dim "  (full multi-stage build: Python + web dashboard + TUI bundle — first build is slow)"
    docker build -f "$REPO_DIR/Dockerfile" -t "$LOCAL_IMAGE" \
      --build-arg HERMES_GIT_SHA="$(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || echo local)" \
      "$REPO_DIR" || { echo "error: image build failed" >&2; return 1; }
  else
    echo "Pulling the published ViloForge preview image…"
    dc pull
  fi
  echo "Starting…"
  dc up -d
  echo
  c_ok "ViloForge Agent preview is up → $URL"
  if [ "$build" = 1 ]; then c_dim "  image: $LOCAL_IMAGE  (built from your working tree)"
  else c_dim "  image: $PUBLISHED_IMAGE  (published; use 'start --build' for local changes)"; fi
  provider_summary
  c_dim "  manage: re-run the launcher with  logs · status · stop · reset"
}

cmd_stop()    { dc down; c_ok "stopped (data volume kept; run 'start' again to resume)"; }
cmd_restart() { cmd_stop; cmd_start "$@"; }
cmd_logs()    { dc logs -f; }

cmd_status() {
  load_secrets
  dc ps
  echo; echo "Seeded providers:"; provider_summary
}

cmd_reset() {
  printf 'This stops the preview and WIPES its data volume. Continue? [y/N] '
  read -r ans
  case "$ans" in y|Y|yes) dc down -v; c_ok "preview stopped and data wiped." ;; *) echo "aborted." ;; esac
}

usage() {
  # print the header comment block (from line 2 until the first non-# line)
  awk 'NR>=2 && /^#/ {sub(/^# ?/,""); print; next} NR>=2 {exit}' "${BASH_SOURCE[0]}"
}

cmd="${1:-start}"
[ "$#" -gt 0 ] && shift
case "$cmd" in
  start|up)    cmd_start "$@" ;;
  --build)     cmd_start --build "$@" ;;   # shorthand for `start --build`
  stop|down)   cmd_stop ;;
  restart)     cmd_restart "$@" ;;
  logs|log)    cmd_logs ;;
  status|ps)   cmd_status ;;
  seed)        cmd_seed ;;
  reset)       cmd_reset ;;
  -h|--help|help) usage ;;
  *) echo "unknown command: $cmd"; echo; usage; exit 1 ;;
esac
