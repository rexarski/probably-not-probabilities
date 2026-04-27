# Probably Not Probabilities

A scrollytelling essay on probability calibration in classification models — what it means, why it matters once you cross a threshold, and how Platt scaling and isotonic regression repair it. Built around a hit-song classifier trained on 114k Spotify tracks.

Live: https://rexarski.github.io/probably-not-probabilities/

## Stack

- **Python** (`python/build_models.py`) — one-shot offline job that trains the three models and emits JSON into `web/static/data/`.
- **SvelteKit 2 + Svelte 5 runes** + **d3** for the article and charts.
- **Bun** for JS package management.
- **KaTeX** for formula typesetting.
- Static deploy via `@sveltejs/adapter-static`.

## Run locally

```bash
# 1. regenerate the data (only needed if you change the Python side)
cd python && uv run build_models.py

# 2. run the site
cd web && bun install && bun run dev
```

Production build:

```bash
cd web && bun run build
```

## Layout

```
python/   model training, emits JSON to web/static/data/
web/      SvelteKit app (the article)
docs/     learning material + GitHub Pages deploy notes
```

See `CLAUDE.md` for architectural decisions and `docs/learning-material.md` for a from-scratch replication guide.
