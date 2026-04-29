# CLAUDE

The goal of this project is to build a scrollytelling website with interactive data visualizations introducing what probability calibration means in classification model, and how we can convey the true meaning of interpretability in machine learning overall. One of the side quest of this article also contains the threshold picking to balance off precision and recall. But we can leave this with some placeholder.

## Compact Instructions

When compressing, preserve in priority order:

1. Architecture decisions (NEVER summarize)
2. Modified files and their key changes
3. Current verification status (pass/fail)
4. Open TODOs and rollback notes
5. Tool outputs (can delete, keep pass/fail only)

## Tech stack

- python for scripting and basic modeling (only used once)
- d3 for interactive visualization (if you have other suggestions you can use that too)
- bun for package managing? (Instead of npm, if this is a good idea)
- svelte for the scrollytelling experience

## Structure

- First let’s start with a medium size (20mb roughly) csv file that contains lots of songs from Spotify. We will use existing features to predict whether the `popularity` will exceeds 80 to determine if a song is a hit song. We don’t need our binary classifier to be a perfect model, we just need it to be appropriately working. And we need the predicted label and true label respectively from a holdout set, let’s say 20%.
    - We will also keep some performance metrics from the holdout set. We will revisit them later.
    - And let’s try to create two such models, one is a little bit overconfident, and the other one is under confident.
- So now you need to writeup the body of the article (this does not need to be a lengthy article, it’s more or less a “show-and-tell” experience, like the articles from **The Pudding**) A couple of takeaways could be highlighted:
    - the model output “score” from classification model demonstrates behavior similar to probabilities but they are different
    - enabling correctness for intervention (0.5 threshold for classification might not always be correct!)
    - calibration methodology and takeaways. There are several available options to consider (sigmoid, isotonic, beta)
    - introduce them by signaling the formula, the definition of brier score, and the rule of thumb scenarios to use them.
    - conclusion and takeaway. **This is not essential for your workflow, but now that you are aware of it. Please feel free to utilize it as appropriate and share your feedback with us.**

## Design

Articles on **The Pudding** has major influence on our design. We want it to be compatible with Spotify’s color palette since we are using the Spotify data. (Black and green, but for readability the body of the text should remain white-ish color, but we can you large chunk of green(Spotify’s green) for underline/highlights and data visualization etc.)

The articles should be single column most of the time but sometimes we allow sidenote show up on the right hand side along side with the visuals or the paragraphs, like the famous [tufts.css](https://edwardtufte.github.io/tufte-css/)’s style.

The visuals should be crisp, clear, and stylish. Remember, a chart without a title is a mistake. We want everything to be perfect.

## Interactions/scrollytelling

The interactions should play along with the writeup, aka the body of the text.

I will divide the article into the following 3 parts, each part we might have different visualizations.

### What is Calibration?

  - Define calibration formally
  - Use animation to show the results of what an over-confident and an under-confident classifiers can behave in terms of “predicting”, i.e. even though they are making the correct guesses, their probabilities/scores are too high, or only slightly higher than the threshold. This animation can show a few slices of tabular data line by line. Then vanish while we scroll down.
  - Show reliability diagram transitioning from well-calibrated → over-confident → under-confident. This is a “scroll-down”-gradual-show-up animation. The reliability diagram stays for a while until the end of the part.
  - Introduce ECE as the summary metric
  - Takeaway: "A calibrated model's scores behave like true probabilities"

### Why It Matters (Enabling Correctness for Intervention)
  
  - Histogram of raw scores + threshold slider
  - Show how miscalibrated scores lead to wrong decisions at any threshold
  - Bin frequency chart showing predicted vs actual gaps
  - Takeaway: "If you use predicted probabilities to make decisions (thresholds, risk scoring, resource allocation), calibration determines whether those decisions are correct"

### How to Calibrate (Methodology)

This part is more like a slide deck showing off formulas and definitions.

  - Sub-section A: Platt scaling — fit a sigmoid post-hoc; presented as a 3-step scrolly (flat sigmoid → steepness only → MLE fit) with a sticky `PlattCurve`. Original brief said "interactive A/B sliders" but that was reverted to scroll-driven steps for consistency with Part 1.
  - Sub-section B: Isotonic regression — non-parametric step function, PAVA. Same 3-step scrolly treatment (5 knots → 16 knots → all knots).
  - Sub-section C: Before/after comparison (3 reliability diagrams side-by-side, auto-cycling raw → Platt → isotonic).
  - Takeaway: "Several options available; Platt is simple and stable, isotonic is flexible but needs more data"

## references

The following references are very important as they contain all the background knowledge information about what you might need to write up the article/build the website.

- https://ploomber.io/blog/calibration-curve/
- https://scikit-learn.org/stable/modules/calibration.html
- https://scikit-learn.org/stable/modules/calibration.html#calibrating-a-classifier
- https://davidrosenberg.github.io/ttml2021/calibration/2.calibration.pdf
- https://developers.google.com/machine-learning/crash-course/classification/prediction-bias
- https://www.cs.cornell.edu/~alexn/papers/calibration.icml05.crc.rev3.pdf

***

## Architecture decisions (do not summarize away)

- **Two roots, one repo.** `python/build_models.py` is a one-shot offline job; `web/` is a fully static SvelteKit site. The only contract between them is the JSON shape of `web/static/data/*.json`. Never invent a runtime API.
- **Bun** is the JS package manager, lockfile is `bun.lock`. `npm`/`pnpm` substitutable but only if both lockfiles updated.
- **SvelteKit 2 + Svelte 5 runes.** State uses `$state`, `$derived`, `$effect`, `$props()` — not the legacy `let`/`$:` syntax. Components receive props via `let { … } = $props()`.
- **`@sveltejs/adapter-static`** with `paths.base` driven by `BASE_PATH` env var so the site works at `/<repo>/` on GitHub Pages and at `/` locally. Helpers in `src/lib/data.js` must honour this — never hand-write absolute paths to `/data/...`.
- **d3** for charts (selection + scales + shapes). One Svelte component per chart in `src/lib/charts/`. No chart library dependency.
- **Scrollytelling** done with a tiny `inView` Svelte action over `IntersectionObserver` — no `scrollama`. Steps live in flow with a `position: sticky` graphic.
- **Formulas typeset with KaTeX** (`web/src/lib/Math.svelte`, imported as `Tex` not `Math` because `Math` shadows the global). KaTeX CSS is imported once in `+layout.svelte`.
- **Hero is 100vh with `scroll-snap-type: y proximity`** on `<html>`; first scroll lands on Part 1, the rest of the page scrolls freely.
- **Color palette is Spotify-noir** (`#0d0d0d` bg, `#1db954` green) with a Tufte-style sidenote gutter.
- **Hit threshold is `popularity >= 32`**, not 80 as in the original brief. Rationale: low-30s is the domain-meaningful floor for Spotify Discover Weekly / Radio surfacing, and yields a balanced ~53/47 class split that the over/under-confident logit transforms can stretch meaningfully. The 80-cutoff path is no longer supported.
- **Per-Part title cards** (`.part-intro`, ~64vh) front each Part as visual gates. `<hr />` dividers were removed in favour of these. `revealOnView` + `.reveal` / `.reveal-step` classes drive fade-up entrances; sliders for Platt/Isotonic were replaced with scroll-driven steps that mirror Part 1's pattern.
- **Type system: serif headers, sans body.** Fraunces (variable, opsz-aware) for h1/h2/h3 + sidenotes; Hanken Grotesk for paragraph body and UI text. Body is `--sans` by default — paragraphs explicitly inherit it. Don't reset `body { font-family: var(--serif) }`.
- **ECE values are gated on Part 1 step 4.** The reliability diagram component accepts an optional `annotations: Record<id, ece>` prop; the page only passes it once the reader scrolls into the ECE/Brier step (`part1Step >= 4`). The old `.ece-grid` legend below the chart is gone — single legend, in-chart annotation block.
- **Brier formula lives in Part 1, not Part 3 §C.** ECE and Brier are both introduced in the "Two metrics, two emphases" step. Part 3 §C now references back instead of re-deriving the formula.
- **Multiclass calibration is covered as §E** (after side-by-side). One-vs-rest Platt/iso, temperature scaling, vector/matrix scaling, Dirichlet — explicitly framed as "harder bookkeeping, same idea". Don't drop this section when refactoring Part 3.

## Files of record

- `python/build_models.py` — emits `metrics.json`, `holdout.json`, `reliability.json`, `calibrated.json`, `sample_rows.json` into `web/static/data/`.
- `web/src/routes/+page.svelte` — the entire article (3 parts + hero + outro).
- `web/src/lib/charts/*.svelte` — `ReliabilityDiagram`, `ScoreHistogram`, `GapBars`, `PlattCurve`, `IsotonicSteps`, `SampleRows`.
- `web/src/lib/Math.svelte` — KaTeX wrapper, exported as `Tex`.
- `web/src/lib/scrollytelling.js` — `inView`, `revealOnView` actions.
- `web/svelte.config.js` — adapter-static + `BASE_PATH` plumbing.
- `docs/learning-material.md` — from-scratch replication guide.
- `docs/deploy-github-pages.md` — Actions workflow + `gh-pages` branch instructions.

## Verification status (last green run)

- `bun run dev` starts cleanly at `:5173`; all five `/data/*.json` return 200.
- `bun run build` produces `build/` via adapter-static (~1.5 s, ~36 KB layout CSS w/ KaTeX bundled).
- ECE separation after 32-cutoff rerun: well 0.030, over 0.099, under 0.087, Platt 0.030, isotonic 0.016. Brier 0.220 / 0.230 / 0.230. Holdout n = 22,800.
- All formulas render in KaTeX; correctness double-checked:
  - Calibration: `Pr[Y=1 | f(X) = p] = p ∀ p ∈ [0,1]` ✓
  - ECE: `ECE = Σ_{b=1}^B (n_b/N) · |p̄_b − ȳ_b|` ✓
  - Platt: `p̂(x) = σ(a·s(x) + b) = 1 / (1 + e^{-(a·s(x)+b)})` ✓
  - Isotonic: `min_f Σ (y_i − f(s_i))²  s.t. f non-decreasing` ✓
  - Brier: `(1/N) Σ (p̂_i − y_i)²` ✓

## Lessons learned (avoid repeating)

- **Never name an import `Math`.** It shadows the global, breaking every `Math.min`/`Math.max` on the page. The KaTeX wrapper is imported as `Tex`.
- **Static-asset URLs need `paths.base`.** Forget it once and the production build 404s every JSON fetch. Always go through `src/lib/data.js`.
- **`scroll-snap-type: mandatory` is hostile** in long-form articles — it traps the reader mid-paragraph. Use `proximity` so only obvious boundaries (hero → Part 1) snap.
- **GitHub Pages strips `_app/`** unless `build/.nojekyll` exists. Bake it into the deploy workflow, not as a manual step.
- **`@sveltejs/adapter-static`** complains about overwriting `build/index.html` with the fallback; that's expected when `prerender.entries: ['*']` and `fallback: 'index.html'` overlap. Cosmetic only.
- **Don't add features beyond what the brief asks.** Threshold-picking is a "side quest" with a placeholder; resist the urge to build it out before the user asks.
- **"Fitted" ≠ "matches the diagonal."** When a reader sees the Platt sigmoid not tracking the reliability curve perfectly, that's the *constraint* of the family, not a bug. Platt is constrained to sigmoids; isotonic is constrained to monotone steps. Make this explicit in copy — the user got confused exactly here.
- **Alpha tuning is hit-rate-dependent.** The over (`alpha=2.5`) and under (`alpha=0.45`) logit-transform constants were originally chosen for a 1% positive class. They happen to also work for ~53% — but if the threshold ever moves again, re-inspect ECE separation before assuming the alphas are still right.
- **Sample-row picks are intentionally curated, not random.** First 3 rows are top-popularity tracks (>90) so most readers recognise them; remaining 3 are teaching examples (overconfident-wrong, underconfident-right). If you re-run `build_models.py` on a different CSV, double-check the famous block still surfaces household names.
- **Sidenotes can't fit display-mode TeX.** The sidenote gutter is 240px; a `Tex display` block at typical KaTeX widths overflows. Put display-mode formulas in the main column. Sidenotes are for italic asides, not equations.

## Done (was: Next steps)

- [x] `.gitignore` covering Python/Node/Bun/SvelteKit/macOS.
- [x] `docs/learning-material.md` — techstack + from-scratch replication.
- [x] `docs/deploy-github-pages.md` — Actions + branch-deploy routes.
- [x] LaTeX rendering for all formulas (KaTeX), correctness double-checked.
- [x] Full-viewport hero with one-scroll-to-Part-1 snap behavior.
- [x] CLAUDE.md updated with decisions, status, lessons.
- [x] Hit threshold lowered to 32; alphas verified clean ECE separation.
- [x] Reliability diagram font sizes bumped for legibility in side viz.
- [x] Platt + Isotonic switched from sliders to 3-step scroll-driven scrolly.
- [x] Per-Part title cards + stronger reveal animations between sections.
- [x] References list ("Further reading") added to outro of `+page.svelte`.
- [x] Body type switched to sans (Hanken Grotesk); headers + sidenotes stay Fraunces.
- [x] Calibration formula moved out of sidenote into main column (no more gutter overflow).
- [x] Sample rows: first three are popularity-95+ household names (Sam Smith, Manuel Turizo, Bad Bunny).
- [x] Tightened section-header → body spacing (h2 24→14, h3 12→6, plus first-paragraph reset).
- [x] ECE annotations deferred to step 4 of Part 1; second legend removed.
- [x] Reliability axes explained with a 2-row example table before the scrolly.
- [x] "Why does the gap appear?" subsection added to Part 1 (objectives, capacity, regularisation, shift).
- [x] Brier formula relocated to Part 1's "Two metrics, two emphases" step; Part 3 §C de-duplicated.
- [x] §E "What about multiclass?" added — top-label vs class-wise, OvR / temperature / vector / Dirichlet.
- [x] Outro reframed as non-prescriptive — calibration is optional unless your scores get read as probabilities.

## Open

- Threshold-picking: still a placeholder per brief; revisit only when explicitly asked.
- Optional: extra design touches (user said "I will give you instructions later").
