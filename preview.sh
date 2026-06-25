#!/usr/bin/env bash
#
# preview.sh — start/stop the ViloForge Agent preview (Tier-1 rebrand) locally.
#
# Quick use:
#   ./preview.sh seed        # one-time: store your DeepSeek key + Claude Code token
#   ./preview.sh start       # pull + run; prints the dashboard URL
#   ./preview.sh stop        # stop (keeps the throwaway data volume)
#   ./preview.sh logs        # follow logs
#   ./preview.sh status      # show what's running + which providers are seeded
#   ./preview.sh reset       # stop + WIPE the throwaway data volume
#
# Credentials are read from a git-ignored .preview.env (see .preview.env.example)
# and passed to the container as env vars — they are never written into the image,
# the repo, or the data volume. The data volume is throwaway and isolated from
# your real ~/.hermes.
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$REPO_DIR/docker-compose.preview.yml"
SECRETS_FILE="${VILOFORGE_PREVIEW_ENV:-$REPO_DIR/.preview.env}"
URL="http://localhost:9119"
DEFAULT_MODEL="deepseek-chat"

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

load_secrets() {
  if [ -f "$SECRETS_FILE" ]; then
    set -a; . "$SECRETS_FILE"; set +a
  fi
  # The model is not a secret; always give it a default so the preview boots ready.
  export HERMES_MODEL="${HERMES_MODEL:-$DEFAULT_MODEL}"
  # Export the keys only when non-empty, so an unset key is NOT passed as "" to the
  # container (compose passes these through with the bare `- VAR` form).
  [ -n "${DEEPSEEK_API_KEY:-}" ] && export DEEPSEEK_API_KEY || unset DEEPSEEK_API_KEY || true
  [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] && export CLAUDE_CODE_OAUTH_TOKEN || unset CLAUDE_CODE_OAUTH_TOKEN || true
}

provider_summary() {
  local any=0
  if [ -n "${DEEPSEEK_API_KEY:-}" ]; then c_ok   "  ✓ DeepSeek            (DEEPSEEK_API_KEY set)"; any=1; fi
  if [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then c_ok "  ✓ Claude Code sub.    (CLAUDE_CODE_OAUTH_TOKEN set)"; any=1; fi
  if [ "$any" = 0 ]; then
    c_warn "  ! no provider keys seeded — the chrome is visible but chat won't work."
    c_dim  "    run: ./preview.sh seed"
  fi
  c_dim "  default model: ${HERMES_MODEL:-$DEFAULT_MODEL}  (switch in the dashboard)"
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
  printf 'Default model [%s]: ' "$DEFAULT_MODEL"
  read -r mdl; mdl="${mdl:-$DEFAULT_MODEL}"

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
  # model always recorded (not a secret)
  grep -vE '^HERMES_MODEL=' "$SECRETS_FILE" > "$SECRETS_FILE.tmp" 2>/dev/null && mv "$SECRETS_FILE.tmp" "$SECRETS_FILE" || true
  printf 'HERMES_MODEL=%s\n' "$mdl" >> "$SECRETS_FILE"

  # Lock down perms LAST — the grep>tmp>mv rewrites above recreate the file with
  # the default umask (644), so chmod must come after every write.
  chmod 600 "$SECRETS_FILE"
  echo; c_ok "Saved. Now: ./preview.sh start"
}

cmd_start() {
  load_secrets
  echo "Pulling ViloForge preview image…"
  dc pull
  echo "Starting…"
  dc up -d
  echo
  c_ok "ViloForge Agent preview is up → $URL"
  provider_summary
  c_dim "logs: ./preview.sh logs   |   stop: ./preview.sh stop"
}

cmd_stop()    { dc down; c_ok "stopped (data volume kept; ./preview.sh start to resume)"; }
cmd_restart() { cmd_stop; cmd_start; }
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

case "${1:-start}" in
  start|up)    cmd_start ;;
  stop|down)   cmd_stop ;;
  restart)     cmd_restart ;;
  logs|log)    cmd_logs ;;
  status|ps)   cmd_status ;;
  seed)        cmd_seed ;;
  reset)       cmd_reset ;;
  -h|--help|help) usage ;;
  *) echo "unknown command: $1"; echo; usage; exit 1 ;;
esac
