# Deploying to GitHub Pages

The site is a fully static SvelteKit build (`@sveltejs/adapter-static`), so GitHub Pages is the path of least resistance. Two routes are documented below — pick one.

- **Route A (recommended):** GitHub Actions builds and publishes on every push to `main`.
- **Route B:** Build locally, push the `build/` output to a `gh-pages` branch.

Both produce the same result; A is hands-off after the initial setup.

---

## 0. Prerequisite: the `BASE_PATH` story

GitHub Pages serves project sites under a sub-path:

```
https://<user>.github.io/<repo>/
```

That sub-path matters for asset URLs. `svelte.config.js` already reads it from an env var:

```js
const base = dev ? '' : process.env.BASE_PATH ?? '';
// kit.paths.base = base
```

So when you build for production you need to set `BASE_PATH` to `/<repo>` (with the leading slash, no trailing slash). The repo is named `probably-not-probabilities`, so:

```
BASE_PATH=/probably-not-probabilities
```

If you ever map a custom domain (`yourdomain.com`) at the root, set `BASE_PATH=""` instead.

> All in-app links should already use `$app/paths`'s `base`, or be relative. Don't hand-write absolute paths like `/data/foo.json` — use `${base}/data/foo.json` or rely on the `loadX()` helpers in `web/src/lib/data.js`.

---

## Route A — GitHub Actions (recommended)

### Step 1 — push the repo to GitHub

```bash
cd /path/to/probably-not-probabilities
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin git@github.com:<user>/probably-not-probabilities.git
git push -u origin main
```

### Step 2 — turn on Pages

On GitHub → **Settings → Pages**:

- **Source:** *GitHub Actions*

(Don't pick "Deploy from a branch" — that's Route B.)

### Step 3 — add the workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy site to GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: web
    steps:
      - uses: actions/checkout@v4

      - uses: oven-sh/setup-bun@v2
        with:
          bun-version: latest

      - name: Install
        run: bun install --frozen-lockfile

      - name: Build
        env:
          BASE_PATH: /probably-not-probabilities
        run: bun run build

      - name: Add .nojekyll
        run: touch build/.nojekyll

      - uses: actions/upload-pages-artifact@v3
        with:
          path: web/build

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

> Why `.nojekyll`? GitHub Pages otherwise runs Jekyll on the output and silently strips files/folders that begin with an underscore (`_app/`), which SvelteKit emits.

### Step 4 — push and watch

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: deploy to github pages"
git push
```

Open the **Actions** tab; the run finishes in 1–2 minutes. The site is live at:

```
https://<user>.github.io/probably-not-probabilities/
```

---

## Route B — local build + `gh-pages` branch

Use this if you can't enable Actions on a private repo, or you just want the simplest possible thing.

### One-time setup

```bash
cd web
bun add -D gh-pages
```

Add to `web/package.json` `scripts`:

```json
"deploy:gh": "BASE_PATH=/probably-not-probabilities bun run build && touch build/.nojekyll && bunx gh-pages -d build -t true"
```

(`-t true` ships dotfiles like `.nojekyll`.)

### Each deploy

```bash
cd web
bun run deploy:gh
```

Then on GitHub → **Settings → Pages**:

- **Source:** *Deploy from a branch*
- **Branch:** `gh-pages` / `/ (root)`

First deploy can take ~1 minute to propagate.

---

## Smoke-testing the build locally before you push

```bash
cd web
BASE_PATH=/probably-not-probabilities bun run build
bun run preview      # serves built static files at http://localhost:4173
```

Open the browser dev tools and confirm:

- `/probably-not-probabilities/data/holdout.json` returns 200
- All five JSON files load (`holdout`, `reliability`, `metrics`, `calibrated`, `sample_rows`)
- No 404s for `/_app/...` chunks
- Charts and threshold sliders behave the same as in `dev`

If you see 404s on `/data/*.json`, you forgot `BASE_PATH`. If charts go blank, check the console — most likely a `paths.base` issue or a chart prop receiving `null` because of failed fetch.

---

## Custom domain (optional)

1. On GitHub → **Settings → Pages → Custom domain**, enter `yourdomain.com`.
2. Add a `CNAME` DNS record pointing your domain at `<user>.github.io`.
3. Either:
   - rebuild with **`BASE_PATH=""`** so assets resolve at the root, **and**
   - add a `web/static/CNAME` file containing `yourdomain.com` (so it's copied into `build/`).
4. Push. The first time, Pages re-issues a Let's Encrypt cert; HTTPS may take a few minutes.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Page loads but is unstyled / no JS runs | `_app/` was stripped by Jekyll | ensure `build/.nojekyll` exists in the artifact |
| 404 on JSON or chunk URLs | `BASE_PATH` missing or wrong | set `BASE_PATH=/<repo>` at build time |
| Page works on `/index.html` but not `/` | adapter `fallback` confusion | keep `fallback: 'index.html'` in `svelte.config.js` |
| Action fails on `bun install --frozen-lockfile` | `bun.lock` out of sync with `package.json` | locally `rm bun.lock && bun install`, commit, push |
| Charts look fine in dev, blank in prod | chart component reading from absolute URL | route through `$lib/data.js` helpers, which honour `paths.base` |

---

## TL;DR

```bash
# Route A (GitHub Actions)
mkdir -p .github/workflows && $EDITOR .github/workflows/deploy.yml   # paste workflow above
git add . && git commit -m "ci: deploy to gh pages" && git push

# then on GitHub: Settings → Pages → Source: GitHub Actions
# done. → https://<user>.github.io/probably-not-probabilities/
```
