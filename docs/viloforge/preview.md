# ViloForge Agent — preview build (runbook)

A hands-on way to run the rebranded agent and evaluate it **before Tier 2**. The
preview is a normal container image published to GHCR from this repo — there is
no separate repo (the registry tag is the distribution unit).

## What this preview is (and isn't)

- **Is:** the **Tier-1 display brand** — the banner, web dashboard, TUI chrome,
  and docs all read *ViloForge*.
- **Isn't:** Tier 2. The Python package is still `hermes-agent`, the command is
  still `hermes`, and the image path is still `ghcr.io/viloforge/hermes-agent`.
  Tier 2 is what renames those — so this is exactly the state to look at before
  deciding it.
- The do-not-touch boundary is intact: you should still see `nousresearch.com`
  links, the "Built by Nous Research" attribution, the Nous Portal provider, and
  the `hermes-3/4` model IDs — those are upstream property and stay (ADR-0003 D4).

## Prerequisites

- Docker + the Compose plugin.
- Provider credentials **only for functional testing** (chatting) — the rebranded
  chrome is visible without any. The preview is wired for two:
  - **DeepSeek** — an API key from <https://platform.deepseek.com/>.
  - **Claude Code subscription** — a long-lived token from `claude setup-token`
    (needs the Claude Code CLI + an active subscription). The preview uses *your*
    subscription quota via the anthropic provider's `claude-code` OAuth path.
- **GHCR access.** If `ghcr.io/viloforge/hermes-agent` is a private package,
  authenticate once with a GitHub token that has `read:packages`:
  ```bash
  echo "$GHCR_PAT" | docker login ghcr.io -u <your-github-username> --password-stdin
  ```
  (Or make the package public in the ViloForge org's package settings.)

## Quick start — `preview.sh`

```bash
./preview.sh seed     # one-time: store your DeepSeek key + Claude Code token
./preview.sh start    # pull + run; prints the dashboard URL + seeded providers
# open http://localhost:9119
./preview.sh logs     # follow logs
./preview.sh stop     # stop (keeps the throwaway data)
./preview.sh reset    # stop + WIPE the throwaway data volume
```

`seed` writes a **git-ignored `.preview.env`** (template: `.preview.env.example`)
and the credentials are passed to the container as env vars at runtime — they are
never committed, baked into the image, or written to the data volume. Data lives in
an **isolated throwaway volume** (`viloforge-preview-data`), not your real
`~/.hermes`. The dashboard embeds the real TUI, so you also see the rebranded chat
surface; switch models live in the dashboard (the seeded default is `HERMES_MODEL`,
`deepseek-chat` out of the box).

### Manual (without the wrapper)

```bash
# put DEEPSEEK_API_KEY / CLAUDE_CODE_OAUTH_TOKEN / HERMES_MODEL in your shell env, then:
docker compose -f docker-compose.preview.yml pull
docker compose -f docker-compose.preview.yml up -d
docker compose -f docker-compose.preview.yml down -v   # stop + wipe
```
The two provider keys use compose **bare passthrough** (`- DEEPSEEK_API_KEY`), so an
unset key is simply not injected (no empty-key errors) and the provider is just
unavailable.

## See the CLI banner / version directly

```bash
# version label (quick branding check — should say ViloForge):
docker run --rm ghcr.io/viloforge/hermes-agent:preview --version

# interactive CLI with the VILOFORGE banner (Ctrl-D to exit):
docker run -it --rm ghcr.io/viloforge/hermes-agent:preview
```
(The image's entrypoint passes any args through to `hermes <args>`.)

## Functional testing (optional)

`./preview.sh seed` prompts for the DeepSeek key and the Claude Code token and
writes `.preview.env`; `./preview.sh start` then boots with them. To add another
provider, drop its var in `.preview.env` and add a matching `- VAR` line to
`docker-compose.preview.yml`. Get the Claude Code token with:
```bash
claude setup-token      # requires the Claude Code CLI + an active subscription
```

## What to verify (rebrand checklist)

**Rebranded (Tier 1 — should say ViloForge):**
- [ ] CLI banner / `--version` label
- [ ] Dashboard `<title>`, header, theme labels
- [ ] TUI chrome inside the dashboard chat

**Preserved (do-not-touch — must NOT be rebranded):**
- [ ] `nousresearch.com` links and the "Built by Nous Research" attribution
- [ ] Nous Portal provider / login option
- [ ] `hermes-3` / `hermes-4` model IDs in the model picker
- [ ] the `hermes` command itself still works (Tier-2/3 deferred)

## How the preview image is produced

The `:preview` tag is published by `.github/workflows/viloforge-publish.yml` on a
manual **Run workflow** (`workflow_dispatch`). To cut a fresh preview from a
branch/tag/SHA:

```bash
gh workflow run viloforge-publish.yml --repo ViloForge/hermes-agent --ref <branch-or-tag>
```

It builds amd64, smoke-tests the image, then pushes
`ghcr.io/viloforge/hermes-agent:preview` (plus `:sha`). `:preview` is a **pinned
evaluation channel**, distinct from the moving `:latest` that every push to
`main` updates.

## Notes / troubleshooting

- **amd64 only.** The publish workflow currently builds `linux/amd64`. On Apple
  Silicon, Docker runs it under emulation (slower but works).
- **Docker Desktop without host networking.** If `localhost:9119` doesn't
  resolve, swap host networking for a published port: remove
  `network_mode: host`, add `ports: ["127.0.0.1:9119:9119"]`, and change the
  command to bind inside the container (`["dashboard", "--host", "0.0.0.0",
  "--no-open"]`). The publish stays host-local (`127.0.0.1:`), so it is not
  exposed to your LAN.
- **Don't bind the dashboard to `0.0.0.0` on a routable interface** without a
  fronting auth proxy — it stores API keys.
