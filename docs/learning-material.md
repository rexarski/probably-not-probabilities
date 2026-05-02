# Learning material: building **Probably Not Probabilities** from scratch

This is the companion read-along for the project. Goal: a single, opinionated walk-through that lets you reproduce a scrollytelling article on probability calibration on a fresh machine — from raw CSV through to a static site you can deploy.

If you're impatient: the **TL;DR** is at the bottom.

---

## 1. The tech stack and *why*

| Layer | Tool | Why this and not something else |
|---|---|---|
| Modeling | **Python** + scikit-learn + pandas + numpy | Calibration is a one-shot offline computation. Python's ML ecosystem is the path of least resistance; we never need it at runtime. |
| Data exchange | **JSON files** in `web/static/data/` | The site is fully static — no server, no API. Whatever the model exports, the browser fetches as a flat file. |
| Package manager (JS) | **Bun** | Fast installs, fast script runner, drop-in for npm. You can substitute `npm`/`pnpm`/`yarn` everywhere below; the lockfile is the only thing that changes. |
| Framework | **SvelteKit 2** (Svelte 5 runes) | Tiny client bundle, first-class static export, fine-grained reactivity that pairs well with scroll-driven UIs. |
| Static export | `@sveltejs/adapter-static` | Produces a folder of HTML/JS/CSS — perfect for GitHub Pages. |
| Charts | **d3** (selection + scales + shape) | We're drawing custom things (sticky reliability diagram, threshold-slider histogram, isotonic step function). d3 gives us scales, axes, and shapes without dragging a chart library's opinions into the article. |
| Scrollytelling | **IntersectionObserver** in a tiny Svelte action (`scrollytelling.js`) | No `scrollama`, no dependency. ~30 lines of code; advances `step` state when an element enters the viewport. |
| Scroll-driven CSS | `animation-timeline: scroll()` / `view()` (progressive enhancement) | Used for the top progress bar and the per-Part title-card reveals. Pure CSS, gated on `@supports`, so unsupported browsers fall back to the IntersectionObserver path. |
| Typography | Inter / Fraunces / JetBrains Mono via Google Fonts | Inter for UI, Fraunces for the editorial body, mono for code/values. |
| Color | Spotify-noir palette (`#0d0d0d` bg, `#1db954` green) | Matches the data source aesthetically; high contrast for charts. |

### Why a static site?

Calibration is a computation we run **once**, on a holdout set we control. The browser only needs to (a) load pre-computed numbers, (b) render charts, (c) react to user input — the threshold-picker in Part 2, and the scroll-driven step builds in Part 3. Nothing about that needs a server, and avoiding one removes a whole class of deployment headaches.

---

## 2. Repository layout

```
probably-not-probabilities/
├── CLAUDE.md                 # project brief / instructions for Claude
├── data/
│   └── spotify_music.csv     # ~20MB raw input (Kaggle "Spotify Tracks Dataset")
├── python/
│   ├── requirements.txt
│   └── build_models.py       # trains 3 classifiers, dumps JSON to web/static/data/
├── web/
│   ├── package.json
│   ├── svelte.config.js
│   ├── vite.config.js
│   ├── src/
│   │   ├── app.html
│   │   ├── routes/+page.svelte         # the entire article
│   │   ├── lib/
│   │   │   ├── data.js                 # fetch helpers
│   │   │   ├── theme.js                # palette tokens used by charts
│   │   │   ├── scrollytelling.js       # `inView` / `revealOnView` actions
│   │   │   ├── Math.svelte             # KaTeX wrapper (imported as `Tex`)
│   │   │   ├── CountUp.svelte          # animates a number from 0→target on view enter
│   │   │   ├── StepDots.svelte         # progress chip-strip for sticky scrollys
│   │   │   ├── IdentityReveal.svelte   # the A/B/C → label pill morph in Part 2
│   │   │   └── charts/                 # one Svelte component per chart
│   │   └── styles/global.css
│   └── static/
│       ├── favicon.svg
│       └── data/                       # outputs of build_models.py (JSON)
└── docs/                               # the doc you are reading lives here
```

**Two roots, one repo.** `python/` and `web/` are deliberately decoupled — the only contract between them is the JSON shape of files in `web/static/data/`.

---

## 3. Prerequisites

Install once on your machine.

| Need | Version | macOS install |
|---|---|---|
| Python | 3.10+ | `brew install python@3.12` |
| Bun | 1.0+ | `curl -fsSL https://bun.sh/install \| bash` |
| (or Node) | 20+ | `brew install node` |
| Git | any | `brew install git` |

Sanity-check:

```bash
python3 --version
bun --version       # or: node --version
```

---

## 4. From zero to running site

### Step 1 — clone (or scaffold) the repo

```bash
git clone https://github.com/<you>/probably-not-probabilities.git
cd probably-not-probabilities
```

If you're scaffolding from nothing instead, the layout in §2 is what to recreate; the rest of this guide tells you what each file does.

### Step 2 — get the data

Download the Spotify Tracks Dataset (~114k rows) from Kaggle and drop it in:

```
data/spotify_music.csv
```

Source: <https://www.kaggle.com/datasets/maharshipandya/-spotify-tracks-dataset>

We treat any track with `popularity >= 32` as a "hit". That's the binary target.

> Why 32? Spotify's editorial systems (Discover Weekly, Radio seeding) tend to require popularity in the low 30s before a track is surfaced, so it's a domain-meaningful cutoff. It also yields a healthy ~53/47 class balance.

### Step 3 — train the three models

```bash
cd python
python3 -m venv .venv
source .venv/bin/activate          # fish: source .venv/bin/activate.fish
pip install -r requirements.txt
python build_models.py
```

This script:

1. Loads `data/spotify_music.csv`, drops non-numeric columns, defines `y = (popularity >= 32)`.
2. Splits 80/20 stratified.
3. Trains a baseline gradient boosting classifier — the **well-calibrated** model.
4. Constructs an **over-confident** sibling by sharpening logits (`logit * 2.5`, pushing scores toward 0 and 1).
5. Constructs an **under-confident** sibling by softening logits (`logit * 0.45`, pulling scores toward 0.5).
6. Computes per-model: histogram bins, reliability bins (mean predicted vs. fraction positive, weighted), ECE, Brier, accuracy, AUC.
7. Fits **Platt scaling** and **isotonic regression** on the over-confident scores.
8. Writes everything to `web/static/data/*.json`:
   - `metrics.json` — summary numbers per model (used by ECE chips and Part 2 cards)
   - `holdout.json` — flat arrays `y_true`, `p_base`, `p_over`, `p_under` for re-bucketing at any threshold
   - `reliability.json` — pre-computed reliability bins per model
   - `calibrated.json` — raw / Platt / isotonic reliabilities + Platt `(a, b)` + isotonic step knots
   - `sample_rows.json` — six tracks with both raw and miscalibrated scores for the Part 1 animation

> Why dump arrays of all holdout scores? Because in Part 2 the user drags a threshold slider and we recompute precision/recall/accuracy in the browser. That requires per-row scores, not bucketed ones.

### Step 4 — install the web deps

```bash
cd ../web
bun install                 # or: npm install
```

### Step 5 — run dev

```bash
bun run dev                 # or: npm run dev
```

Visit <http://localhost:5173>. You should see the hero, three article sections with per-Part title cards and sticky charts. Part 2's histogram has a draggable threshold; Part 3's Platt and isotonic mini-stories advance as you scroll.

### Step 6 — build static site

```bash
bun run build               # or: npm run build
bun run preview             # serves the static `build/` folder
```

`build/` is a folder of pure HTML/JS/CSS — copy it anywhere static. For GitHub Pages specifically, see `docs/deploy-github-pages.md`.

---

## 5. Interactive polish

The article gets most of its feel from a handful of small, composable patterns. Each is independently optional — pull any one out and the piece still reads — but together they're what separates "a chart with a caption" from a Pudding-style explainer.

### 5.1 Hover/tap tooltips on data marks

The reliability dots, histogram bars, and gap bars (`ReliabilityDiagram.svelte`, `ScoreHistogram.svelte`, `GapBars.svelte`) attach `pointerenter` / `pointermove` / `pointerleave` directly to each mark. The handler computes pointer position relative to the figure's bounding rect and stores `{x, y, ...content}` in component state; an absolutely-positioned HTML `<div>` renders the popover. Tooltips auto-flip when the pointer is past 60% of the figure width so they never overflow the right edge. Information density jumps without taxing the static layout.

### 5.2 Count-up on entry — `CountUp.svelte`

Headline numbers (precision, recall, the four confusion-matrix counts) tween from 0 to value over ~700ms when the stat block first crosses the viewport. The component is ~50 lines:

- `IntersectionObserver` with `threshold: 0.4` flips a `played` flag once.
- `requestAnimationFrame` loop with cubic-out easing.
- After `played`, an `$effect` keeps `display = value`, so live values (e.g., the threshold-driven precision/recall) update normally without re-tweening.
- Honours `prefers-reduced-motion` by short-circuiting to the final value on mount.

It accepts a `format` function (`(v) => '${v.toFixed(1)}%'`) so the same component handles percentages, integers, and decimals without branching internally.

### 5.3 Sticky scrolly indicators — `StepDots.svelte`

The Platt and isotonic scrollys each have three steps with a shared sticky chart. Without an indicator the reader can lose their place; with one, the chart and prose stay visibly paired. `StepDots` renders a horizontal chip strip (`flat sigmoid · steepness · MLE fit`), where the active chip glows green and past chips show a dim-green completed state. CSS-only animation. Pairs with a one-line global rule (`.scrolly .step.is-visible:not(.active) { opacity: 0.42 }`) that dims non-active step prose so the active step alone owns the chart change.

### 5.4 Scroll-driven CSS (progressive enhancement)

Two places use `animation-timeline` directly, gated on `@supports (animation-timeline: ...)`:

- **Top progress bar** (`+layout.svelte`): a fixed 2px green strip with `transform-origin: 0 50%` and `animation-timeline: scroll(root block)` keyframing `transform: scaleX(0) → scaleX(1)`. Pure CSS.
- **Per-Part title card reveal** (`global.css`): the tag/title/blurb inside `.part-intro` each get an `animation-name: part-intro-rise` with staggered `animation-range` (`entry 0% cover 18%` → `... 30%` → `... 42%`), tied to `animation-timeline: view()`. Reader scrubs the reveal as the card crosses the viewport.

In both cases, browsers without support fall through to the JS `revealOnView` / static-display path. `@media (prefers-reduced-motion: reduce)` short-circuits both.

### 5.5 The A/B/C reveal — `IdentityReveal.svelte`

The article's biggest moment is the curtain-lift in Part 2: the placeholder names A, B, C give way to *well-calibrated*, *over-confident*, *under-confident*. Three colored pills sit before the bridge paragraph; on `IntersectionObserver` enter, each pill expands (`max-width: 0 → 200px`) with a 160ms stagger, the label fades in, and a soft color glow blooms behind the pill via `box-shadow`. A textual reveal made visual, in ~80 lines.

### 5.6 Inline model tagging — `.mt`/`.mt-a/b/c`

Body prose mentions of *Model A/B/C* carry a 7px colored dot prefix matching the chart hue. CSS-only:

```css
.mt::before {
  content: '';
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--mt-c, currentColor);
}
.mt-a { --mt-c: #1db954; }
.mt-b { --mt-c: #ff7a59; }
.mt-c { --mt-c: #7ab7ff; }
```

The eye loops between paragraph and chart in one saccade instead of two. Cheap, high-leverage.

---

## 6. Concepts to take away

These are what the article and the codebase are really about. Worth re-deriving once you've shipped this.

1. **A "score" is not a probability.** It quacks like one — bounded in `[0, 1]`, rises with confidence — but the only way it earns the name is empirical: among predictions of `0.7`, do ~70% turn out positive?
2. **Calibration ≠ accuracy ≠ ranking.** Three orthogonal properties. AUC can be perfect on a model whose probabilities are systematically wrong. Accuracy can be high while every score is over- or under-shot.
3. **Reliability diagrams** are the single best diagnostic. Bin scores, plot mean predicted vs. fraction positive. Diagonal = calibrated.
4. **ECE summarises that gap** in one number; **Brier** does the same in expectation but penalises distance, not just bias.
5. **Calibration is post-hoc and cheap.** You don't retrain. You fit a 1D monotone map (Platt: 2 parameters; isotonic: a step function) on a holdout slice.
6. **Rule of thumb.** Platt with <1k calibration samples; isotonic with ≥1k. Beta calibration for very large sets if you need it.
7. **Decisions ≠ ranking.** Any time you compare a score to a threshold to *act* — promote, alert, allocate — calibration determines whether that act is correct. Ranking metrics will not warn you.

---

## 7. Where to go next

- **Threshold-picking.** This article hand-waves it; the proper version is "pick the threshold that minimises expected cost given your false-positive / false-negative ratios". Build a precision/recall curve with a draggable cost ratio.
- **Beta calibration.** Add it as a third option in Part 3. Three params instead of two; sometimes wins.
- **Multi-class.** Generalise to one-vs-rest reliability per class.

---

## TL;DR

```bash
# one-time
git clone <repo> && cd probably-not-probabilities

# data
mv ~/Downloads/spotify_music.csv data/

# train + emit JSON
cd python && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && python build_models.py && cd ..

# run the site
cd web && bun install && bun run dev      # → http://localhost:5173
```

That's it.
