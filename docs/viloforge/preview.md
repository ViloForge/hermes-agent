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
- A model-provider API key **only for functional testing** (chatting). The
  rebranded chrome is visible without one.
- **GHCR access.** If `ghcr.io/viloforge/hermes-agent` is a private package,
  authenticate once with a GitHub token that has `read:packages`:
  ```bash
  echo "$GHCR_PAT" | docker login ghcr.io -u <your-github-username> --password-stdin
  ```
  (Or make the package public in the ViloForge org's package settings.)

## Quick start (dashboard)

```bash
docker compose -f docker-compose.preview.yml pull
docker compose -f docker-compose.preview.yml up -d
# open the dashboard:
xdg-open http://localhost:9119   # or just browse to it
docker compose -f docker-compose.preview.yml logs -f   # watch startup
```

The dashboard embeds the real TUI, so you see the rebranded chat surface too.
Data lives in an **isolated throwaway volume** (`viloforge-preview-data`), not
your real `~/.hermes`.

Tear down (and wipe the throwaway data):
```bash
docker compose -f docker-compose.preview.yml down -v
```

## See the CLI banner / version directly

```bash
# version label (quick branding check — should say ViloForge):
docker run --rm ghcr.io/viloforge/hermes-agent:preview --version

# interactive CLI with the VILOFORGE banner (Ctrl-D to exit):
docker run -it --rm ghcr.io/viloforge/hermes-agent:preview
```
(The image's entrypoint passes any args through to `hermes <args>`.)

## Functional testing (optional)

To actually chat, give the container a provider key — either uncomment one in the
`environment:` block of `docker-compose.preview.yml`, or put it in an `.env` file
beside the compose, e.g.:
```
OPENROUTER_API_KEY=sk-or-...
```
then `docker compose -f docker-compose.preview.yml up -d` again.

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
