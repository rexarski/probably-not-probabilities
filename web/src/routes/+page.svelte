<script>
  import { onMount } from 'svelte';
  import {
    loadHoldout,
    loadReliability,
    loadMetrics,
    loadCalibrated,
    loadSampleRows
  } from '$lib/data.js';
  import { palette } from '$lib/theme.js';
  import { inView, revealOnView } from '$lib/scrollytelling.js';

  import HeroMosaic from '$lib/HeroMosaic.svelte';
  import ReliabilityDiagram from '$lib/charts/ReliabilityDiagram.svelte';
  import ScoreHistogram from '$lib/charts/ScoreHistogram.svelte';
  import GapBars from '$lib/charts/GapBars.svelte';
  import PlattCurve from '$lib/charts/PlattCurve.svelte';
  import IsotonicSteps from '$lib/charts/IsotonicSteps.svelte';
  import SampleRows from '$lib/charts/SampleRows.svelte';
  import Tex from '$lib/Math.svelte';

  /** @type {any} */ let holdout = $state(null);
  /** @type {any} */ let reliability = $state(null);
  /** @type {any} */ let metrics = $state(null);
  /** @type {any} */ let calibrated = $state(null);
  /** @type {any[]} */ let sampleRows = $state([]);

  // ----- Part 1 state -----
  let part1Step = $state(0); // 0 = sample rows, 1 = well, 2 = over, 3 = under, 4 = ECE
  let visibleRows = $state(0);

  // ----- Part 2 state -----
  let modelChoice = $state('over_confident'); // 'well_calibrated' | 'over_confident' | 'under_confident'
  let threshold = $state(0.5);

  // ----- Part 3 state -----
  // Scroll-driven steps for the Platt and isotonic mini-stories.
  // Both default to 0 (pre-view neutral state) and advance to the
  // fitted/full configuration as the reader scrolls past each step.
  let plattStep = $state(0); // 0 = pre-view, 1 = identity, 2 = steepness only, 3 = MLE fit
  let isoStep = $state(0);   // 0 = pre-view, 1 = coarse, 2 = mid, 3 = full
  let calibMethod = $state('platt'); // 'raw' | 'platt' | 'isotonic'

  // Platt curve parameters per step
  const plattAByStep = $derived.by(() => {
    const fitted = calibrated?.platt?.params?.a ?? 2.9;
    switch (plattStep) {
      case 0: return 1;
      case 1: return 1;
      case 2: return 5;
      default: return fitted; // step 3
    }
  });
  const plattBByStep = $derived.by(() => {
    const fitted = calibrated?.platt?.params?.b ?? -1.5;
    switch (plattStep) {
      case 0: return 0;
      case 1: return 0;
      case 2: return 0;
      default: return fitted; // step 3
    }
  });

  // Isotonic knot count per step (0 in component = "all")
  const isoKnotsByStep = $derived.by(() => {
    switch (isoStep) {
      case 0: return 5;
      case 1: return 5;
      case 2: return 16;
      default: return 0; // full PAVA
    }
  });
  const isoProbeByStep = $derived(isoStep >= 3 ? 0.7 : isoStep === 2 ? 0.55 : 0.4);

  onMount(async () => {
    [holdout, reliability, metrics, calibrated, sampleRows] = await Promise.all([
      loadHoldout(),
      loadReliability(),
      loadMetrics(),
      loadCalibrated(),
      loadSampleRows()
    ]);
  });

  // Cycle the sample rows on a timer once the figure is in view.
  // Track in-view + data-loaded separately so whichever resolves last can
  // still kick off the animation.
  let rowTimer;
  let rowsInView = $state(false);
  let rowAnimDone = $state(false);

  function tickRowAnim() {
    if (rowTimer || rowAnimDone || !rowsInView || !sampleRows.length) return;
    rowTimer = setInterval(() => {
      visibleRows = Math.min(sampleRows.length, visibleRows + 1);
      if (visibleRows >= sampleRows.length) {
        clearInterval(rowTimer);
        rowTimer = null;
        rowAnimDone = true;
      }
    }, 700);
  }
  function startRowAnim() {
    rowsInView = true;
    tickRowAnim();
  }
  function stopRowAnim() {
    rowsInView = false;
  }
  $effect(() => {
    // re-check when sampleRows arrives after the figure is already in view
    if (sampleRows.length && rowsInView) tickRowAnim();
  });

  // ----- Reliability series for Part 1 (filtered by step) -----
  const seriesAll = $derived.by(() => {
    if (!reliability) return [];
    return [
      {
        id: 'well_calibrated',
        label: 'Well-calibrated',
        color: palette.wellCalibrated,
        points: reliability.well_calibrated
      },
      {
        id: 'over_confident',
        label: 'Over-confident',
        color: palette.overConfident,
        points: reliability.over_confident
      },
      {
        id: 'under_confident',
        label: 'Under-confident',
        color: palette.underConfident,
        points: reliability.under_confident
      }
    ];
  });

  const part1Active = $derived(
    part1Step === 1
      ? 'well_calibrated'
      : part1Step === 2
        ? 'over_confident'
        : part1Step === 3
          ? 'under_confident'
          : null
  );

  // ----- Part 2 derived -----
  const part2Model = $derived(metrics?.models?.[modelChoice]);
  const part2Reliability = $derived(reliability?.[modelChoice] ?? []);
  const part2Color = $derived(
    modelChoice === 'well_calibrated'
      ? palette.wellCalibrated
      : modelChoice === 'over_confident'
        ? palette.overConfident
        : palette.underConfident
  );

  // Decision counts at current threshold from raw scores
  const decisionStats = $derived.by(() => {
    if (!holdout) return null;
    const arr =
      modelChoice === 'well_calibrated'
        ? holdout.p_base
        : modelChoice === 'over_confident'
          ? holdout.p_over
          : holdout.p_under;
    let tp = 0,
      fp = 0,
      tn = 0,
      fn = 0;
    for (let i = 0; i < arr.length; i++) {
      const yhat = arr[i] >= threshold ? 1 : 0;
      const y = holdout.y_true[i];
      if (yhat === 1 && y === 1) tp++;
      else if (yhat === 1 && y === 0) fp++;
      else if (yhat === 0 && y === 0) tn++;
      else fn++;
    }
    const precision = tp + fp === 0 ? 1 : tp / (tp + fp);
    const recall = tp + fn === 0 ? 0 : tp / (tp + fn);
    const accuracy = (tp + tn) / arr.length;
    return { tp, fp, tn, fn, precision, recall, accuracy, n: arr.length };
  });

  // ----- Part 3 derived -----
  let part3Active = $state(/** @type {null | 'raw' | 'platt' | 'isotonic'} */ (null));
  let part3Cycle = $state(false);
  const part3Reliability = $derived.by(() => {
    if (!calibrated) return [];
    return [
      {
        id: 'raw',
        label: 'Raw (over-confident)',
        color: palette.raw,
        points: calibrated.raw.reliability
      },
      {
        id: 'platt',
        label: 'After Platt',
        color: palette.platt,
        points: calibrated.platt.reliability
      },
      {
        id: 'isotonic',
        label: 'After isotonic',
        color: palette.isotonic,
        points: calibrated.isotonic.reliability
      }
    ];
  });

  // Auto-cycle highlight raw → platt → isotonic when the comparison chart
  // is in view, so the reader sees the curves bend back to the diagonal one
  // at a time. User clicks override.
  let cycleTimer;
  $effect(() => {
    if (part3Cycle) {
      const order = ['raw', 'platt', 'isotonic'];
      let i = 0;
      part3Active = order[i];
      cycleTimer = setInterval(() => {
        i = (i + 1) % order.length;
        part3Active = order[i];
      }, 1800);
      return () => clearInterval(cycleTimer);
    }
  });
  function startCycle() { if (part3Active === null) part3Cycle = true; }
  function stopCycle() { part3Cycle = false; }
</script>

<svelte:head>
  <title>Probably Not Probabilities — a calibration walk-through</title>
</svelte:head>

<main class="page">
  <!-- ============================== HERO ============================== -->
  <header class="hero">
    <HeroMosaic />
    <p class="kicker">On probability calibration</p>
    <h1>
      Probably <span class="green">Not</span><br />
      Probabilities
    </h1>
    <p class="lede col">
      Classification models hand you a number between zero and one. It looks like a
      probability. It quacks like a probability. We treat it like a probability — set a
      threshold at <code>0.5</code>, ship the decision, move on. But that number is
      really only a <em class="term">score</em>. Whether it behaves like a true
      probability is a separate question entirely. That question is called
      <em class="term">calibration</em>, and it's what this piece is about.
    </p>
    <p class="lede col" style="color: var(--ink-soft); font-size: 16px;">
      We trained two flavours of a hit-song classifier on
      <a href="https://www.kaggle.com/datasets/maharshipandya/-spotify-tracks-dataset" target="_blank" rel="noreferrer">114k Spotify tracks</a>
      — one made over-confident, one under-confident — to see what miscalibration
      actually looks like, why it ruins downstream decisions, and how two classic
      tricks (Platt scaling and isotonic regression) repair it.
    </p>
    <div class="scroll-cue" aria-hidden="true">scroll</div>
  </header>

  <!-- ============================== PART 1 ============================== -->
  <section class="part part-1">
    <div class="part-intro reveal" use:revealOnView>
      <p class="part-tag">Part&nbsp;1</p>
      <h2 class="title-card">What is <span class="accent">calibration</span>?</h2>
      <p class="part-blurb">
        Three classifiers, one ranking — and three completely different stories
        about what their scores actually mean.
      </p>
    </div>

    <div class="with-sidenote reveal" use:revealOnView>
      <div class="col">
        <p>
          A classifier is <em class="term">calibrated</em> when, among all the cases it
          rates around <code>p</code>, roughly a <code>p</code>-fraction are actually
          positive. So among songs the model labels with score 0.7, about 70&nbsp;% of
          them really are popular hits. Calibration is a property of the score, not of
          the prediction.
        </p>
      </div>
      <aside class="sidenote">
        Formally: a model <code>f</code> is calibrated when
        <Tex tex={'\\Pr[\\,Y=1 \\mid f(X)=p\\,] = p \\quad \\forall\\, p \\in [0,1].'} display />
        Accuracy and ranking quality are different properties — a model can be perfectly
        accurate yet badly calibrated, and vice-versa.
      </aside>
    </div>

    <p class="col">
      The two models below make almost the same <em>decisions</em> at threshold 0.5 —
      they're roughly tied on accuracy. But their <em>scores</em> tell completely
      different stories. Watch how an over-confident model crowds tracks toward 0&nbsp;and
      1, while an under-confident one keeps everything bunched around the middle.
    </p>

    {#if sampleRows.length}
      <div
        class="rows-figure col-wide"
        use:inView={{ onEnter: startRowAnim, onExit: stopRowAnim, threshold: 0.15, rootMargin: '0px' }}>
        <SampleRows rows={sampleRows} visibleCount={visibleRows} />
        <p class="caption">
          Six tracks from the holdout set. Both models score them — yet one is
          theatrical and the other is timid. The decision at <code>t = 0.5</code> is
          the same in many rows, even when the score moves from 0.05 to 0.85.
        </p>
      </div>
    {/if}

    <!-- Sticky reliability scrolly -->
    <h3 style="margin-top: 100px;">The reliability diagram</h3>
    <p class="col">
      To <em>see</em> calibration, we plot predicted score against the actual fraction
      of hits in each score bin. A perfect model traces the diagonal. Anything else
      tells you, at a glance, where the model is over- or under-shooting.
    </p>

    <div class="scrolly">
      <div class="steps">
        <div
          class="step reveal-step" use:revealOnView
          use:inView={{ onEnter: () => (part1Step = 1), threshold: 0.6 }}>
          <h3>Well-calibrated</h3>
          <p>
            The well-trained gradient boosting model hugs the diagonal. When it says
            <code>0.6</code>, about 60&nbsp;% of those tracks really are popular. Its
            <em class="term">expected calibration error</em> on the holdout set is
            small.
          </p>
        </div>
        <div
          class="step reveal-step" use:revealOnView
          use:inView={{ onEnter: () => (part1Step = 2), threshold: 0.6 }}>
          <h3>Over-confident</h3>
          <p>
            We squash this model's logits outward, so its scores live near 0 and 1.
            It's still right at threshold 0.5 — but when it says <code>0.95</code>, the
            actual hit rate is closer to <code>0.7</code>. The curve drops below the
            diagonal at the top, climbs above it at the bottom.
          </p>
        </div>
        <div
          class="step reveal-step" use:revealOnView
          use:inView={{ onEnter: () => (part1Step = 3), threshold: 0.6 }}>
          <h3>Under-confident</h3>
          <p>
            The opposite move pulls scores toward <code>0.5</code>. The model never
            commits. When it whispers <code>0.55</code>, the actual hit rate is more
            like <code>0.7</code>. Below 0.5, it's similarly too shy.
          </p>
        </div>
        <div
          class="step reveal-step" use:revealOnView
          use:inView={{ onEnter: () => (part1Step = 4), threshold: 0.6 }}>
          <h3>One number to summarise the gap</h3>
          <p>
            <em class="term">Expected Calibration Error</em> (ECE) bins predictions and
            averages the absolute gap between mean predicted score and observed hit
            rate, weighted by bin size. Lower is better. <em class="term">Brier score</em>
            does the same job in expectation but penalises distance, not just bias.
          </p>
          <Tex
            display
            tex={'\\mathrm{ECE} \\;=\\; \\sum_{b=1}^{B} \\frac{n_b}{N}\\,\\bigl|\\,\\overline{p}_b \\;-\\; \\overline{y}_b\\,\\bigr|'} />
        </div>
      </div>
      <div class="sticky">
        {#if reliability}
          <ReliabilityDiagram
            series={seriesAll}
            activeId={part1Active}
            title="Reliability diagram — three flavours"
            subtitle="x: mean predicted score per bin · y: actual fraction of hits · circles sized by bin count" />
          {#if metrics?.models}
            <div class="ece-grid">
              <div class="ece" class:active={part1Active === 'well_calibrated'}>
                <span class="ece-dot" style:background={palette.wellCalibrated}></span>
                <span class="ece-l">well-calibrated</span>
                <span class="ece-v">{metrics.models.well_calibrated.ece.toFixed(3)}</span>
              </div>
              <div class="ece" class:active={part1Active === 'over_confident'}>
                <span class="ece-dot" style:background={palette.overConfident}></span>
                <span class="ece-l">over-confident</span>
                <span class="ece-v">{metrics.models.over_confident.ece.toFixed(3)}</span>
              </div>
              <div class="ece" class:active={part1Active === 'under_confident'}>
                <span class="ece-dot" style:background={palette.underConfident}></span>
                <span class="ece-l">under-confident</span>
                <span class="ece-v">{metrics.models.under_confident.ece.toFixed(3)}</span>
              </div>
            </div>
          {/if}
        {/if}
      </div>
    </div>

    <p class="col take" use:revealOnView>
      <strong>Takeaway.</strong> A calibrated model's scores behave like true
      probabilities. If yours don't — and most don't, out of the box — anything you do
      with those scores beyond ranking is on shaky ground.
    </p>
  </section>

  <!-- ============================== PART 2 ============================== -->
  <section class="part part-2">
    <div class="part-intro reveal" use:revealOnView>
      <p class="part-tag">Part&nbsp;2</p>
      <h2 class="title-card">Why it <span class="accent">matters</span></h2>
      <p class="part-blurb">
        Ranking is forgiving. Decisions aren't — and the moment a score crosses
        a threshold, miscalibration turns into wrong answers.
      </p>
    </div>

    <div class="with-sidenote reveal" use:revealOnView>
      <div class="col">
        <p>
          Ranking is forgiving: it only cares about order, and our three models all
          rank the same. <em>Decisions</em> aren't. The moment you compare a score to a
          threshold — to send a song to a "promote" queue, to alert a doctor, to flag
          a transaction — you're treating that score as if it meant something.
          Miscalibration silently changes what your threshold buys you.
        </p>
      </div>
      <aside class="sidenote">
        Threshold 0.5 is convention, not law. The right cutoff depends on the cost
        ratio between false positives and false negatives — and on whether the score
        you're cutting against is a probability in the first place.
      </aside>
    </div>

    <div class="pill-row col">
      {#each [
        { id: 'well_calibrated', label: 'Well-calibrated' },
        { id: 'over_confident', label: 'Over-confident' },
        { id: 'under_confident', label: 'Under-confident' }
      ] as opt}
        <button
          class="pill"
          class:active={modelChoice === opt.id}
          onclick={() => (modelChoice = opt.id)}>
          {opt.label}
        </button>
      {/each}
    </div>

    <p class="col">
      Drag the <em>threshold</em> below — or click anywhere on the histogram — to see
      what changes when you decide a different point is "promote-worthy".
    </p>

    {#if part2Model && decisionStats}
      <div class="figure-grid col-wide">
        <ScoreHistogram
          bins={part2Model.histogram}
          {threshold}
          color={part2Color}
          onThreshold={(t) => (threshold = t)}
          title="Score distribution — {modelChoice.replace('_', ' ')}"
          subtitle="Click or drag to pick a threshold" />

        <div class="stats">
          <div class="stat">
            <div class="label">Threshold</div>
            <div class="value">{threshold.toFixed(2)}</div>
          </div>
          <div class="stat">
            <div class="label">Precision</div>
            <div class="value">{(decisionStats.precision * 100).toFixed(1)}%</div>
            <div class="delta">tp / (tp + fp)</div>
          </div>
          <div class="stat">
            <div class="label">Recall</div>
            <div class="value">{(decisionStats.recall * 100).toFixed(1)}%</div>
            <div class="delta">tp / (tp + fn)</div>
          </div>
          <div class="stat">
            <div class="label">Accuracy</div>
            <div class="value">{(decisionStats.accuracy * 100).toFixed(1)}%</div>
            <div class="delta">over {decisionStats.n.toLocaleString()} tracks</div>
          </div>
        </div>

        <div class="confusion">
          <div class="cm cm-tp"><span>true positives</span><b>{decisionStats.tp.toLocaleString()}</b></div>
          <div class="cm cm-fp"><span>false positives</span><b>{decisionStats.fp.toLocaleString()}</b></div>
          <div class="cm cm-fn"><span>false negatives</span><b>{decisionStats.fn.toLocaleString()}</b></div>
          <div class="cm cm-tn"><span>true negatives</span><b>{decisionStats.tn.toLocaleString()}</b></div>
        </div>

        <p class="col" style="grid-column: 1 / -1; margin-top: 12px;">
          The over-confident model puts almost everything past 0.9 or below 0.1, so
          your threshold barely moves the count of "yes" decisions until you cross
          that wall. The under-confident model is the opposite: every threshold inside
          [0.3, 0.7] reshuffles thousands of tracks. <strong>Same ranking, very
          different operating curves.</strong>
        </p>

        <GapBars
          points={part2Reliability}
          color={part2Color}
          title="Predicted score vs. actual hit rate, per bin"
          subtitle="Bars: mean predicted score in the bin. Black rule: actual hit rate. The gap is calibration error." />
      </div>
    {/if}

    <p class="col take" use:revealOnView>
      <strong>Takeaway.</strong> If you use predicted scores to <em>make decisions</em>
      — thresholds, risk scoring, expected-value math, resource allocation — calibration
      is what determines whether those decisions are actually correct. Ranking-only
      metrics like AUC will tell you everything is fine right up until the point your
      thresholds start lying.
    </p>
  </section>

  <!-- ============================== PART 3 ============================== -->
  <section class="part part-3">
    <div class="part-intro reveal" use:revealOnView>
      <p class="part-tag">Part&nbsp;3</p>
      <h2 class="title-card">How to <span class="accent">calibrate</span></h2>
      <p class="part-blurb">
        Two classic post-hoc fixes — Platt scaling and isotonic regression.
      </p>
    </div>

    <p class="col reveal" use:revealOnView>
      The good news: you don't need to retrain the model. Calibration is a
      <em class="term">post-hoc</em> step. You take the model's raw scores on a held-out
      slice of data, learn a monotone function that maps those scores to actual hit
      rates, and then apply it at inference time.
    </p>

    <h3>A. Platt scaling</h3>
    <div class="with-sidenote">
      <div class="col">
        <p>
          Platt scaling fits a one-dimensional logistic regression on top of the
          model's score:
        </p>
        <Tex display tex={'\\hat{p}(x) \\;=\\; \\sigma\\!\\bigl(a\\cdot s(x) + b\\bigr) \\;=\\; \\frac{1}{1 + e^{-(a\\,s(x) + b)}}'} />
        <p>
          where <code>s(x)</code> is the raw score and <code>a, b</code> are the
          maximum-likelihood estimates from the calibration set. Two parameters — fast,
          stable, works with very little data. The drawback: a sigmoid can only undo
          S-shaped distortions; if the underlying miscalibration has a different shape,
          Platt won't fully close the gap.
        </p>
      </div>
      <aside class="sidenote">
        Originally proposed by John Platt (1999) to extract probabilities from SVM
        decision values, which by construction don't have a probabilistic meaning at
        all.
      </aside>
    </div>

    <div class="scrolly">
      <div class="steps">
        <div class="step reveal-step" use:revealOnView use:inView={{ onEnter: () => (plattStep = 1), threshold: 0.6 }}>
          <h3>Step 1 — A flat sigmoid</h3>
          <p>
            Start with <code>a&nbsp;=&nbsp;1, b&nbsp;=&nbsp;0</code>. The map is
            σ(s) — gentle, almost a straight line over [0, 1]. It barely changes the
            scores. Useless as a calibrator, but a clear baseline.
          </p>
        </div>
        <div class="step reveal-step" use:revealOnView use:inView={{ onEnter: () => (plattStep = 2), threshold: 0.6 }}>
          <h3>Step 2 — Crank the steepness</h3>
          <p>
            Push <code>a</code> up to 5, leave <code>b</code> at 0. Now the curve has
            slope, but it's anchored at the wrong place — saturating from the left
            edge, never lingering near the diagonal. <code>b</code> still needs to do
            its job.
          </p>
        </div>
        <div class="step reveal-step" use:revealOnView use:inView={{ onEnter: () => (plattStep = 3), threshold: 0.6 }}>
          <h3>Step 3 — The MLE fit</h3>
          <p>
            Solve for <code>(a, b)</code> that maximise the log-likelihood of the
            calibration labels. Result:
            <code>a&nbsp;=&nbsp;{plattAByStep.toFixed(2)}</code>,
            <code>b&nbsp;=&nbsp;{plattBByStep.toFixed(2)}</code>.
            <em>This is the fitted Platt scaler.</em>
          </p>
          <p style="color: var(--ink-soft); font-size: 15px; margin-top: 12px;">
            "Fitted" doesn't mean the curve traces the diagonal exactly — it means
            <em>those parameters maximise likelihood under the sigmoid family.</em>
            Any residual bend is an artefact of the family being too restrictive.
            That's exactly the gap isotonic closes next.
          </p>
        </div>
      </div>
      <div class="sticky">
        <PlattCurve a={plattAByStep} b={plattBByStep} />
      </div>
    </div>

    <h3>B. Isotonic regression</h3>
    <div class="with-sidenote">
      <div class="col">
        <p>
          Isotonic regression drops the parametric assumption. Given pairs
          <code>(score, label)</code>, it finds the best non-decreasing step function
          mapping scores to probabilities — solved efficiently by the
          <em class="term">Pool Adjacent Violators</em> (PAVA) algorithm. More flexible than
          Platt, but it can overfit on small calibration sets, since each step is
          essentially a free parameter.
        </p>
        <Tex display tex={'\\min_{f}\\; \\sum_{i=1}^{N}\\bigl(y_i - f(s_i)\\bigr)^2 \\quad \\text{s.t. } f \\text{ non-decreasing}'} />
      </div>
      <aside class="sidenote">
        Rule of thumb: Platt for &lt;1k calibration samples, isotonic for ≥1k. For very
        large sets, Bayesian Beta calibration sometimes beats both, but it's a
        smaller-impact win.
      </aside>
    </div>

    {#if calibrated?.isotonic?.steps}
      <div class="scrolly">
        <div class="steps">
          <div class="step reveal-step" use:revealOnView use:inView={{ onEnter: () => (isoStep = 1), threshold: 0.6 }}>
            <h3>Step 1 — A coarse staircase</h3>
            <p>
              Just five knots. The PAVA solution is forced into a few wide plateaus —
              clearly not flexible enough to track a real distortion, but enough to
              show what "monotone step function" means.
            </p>
          </div>
          <div class="step reveal-step" use:revealOnView use:inView={{ onEnter: () => (isoStep = 2), threshold: 0.6 }}>
            <h3>Step 2 — More resolution</h3>
            <p>
              Sixteen knots. The staircase starts to bend with the data, hugging the
              diagonal more closely. Every additional knot is a free parameter the
              algorithm can spend.
            </p>
          </div>
          <div class="step reveal-step" use:revealOnView use:inView={{ onEnter: () => (isoStep = 3), threshold: 0.6 }}>
            <h3>Step 3 — The full PAVA fit</h3>
            <p>
              Every unique calibration sample becomes a candidate knot, and PAVA
              merges adjacent pairs whenever monotonicity is violated. The result is
              the <em>fitted</em> isotonic regression — non-parametric, no shape
              assumption beyond "non-decreasing".
            </p>
            <p style="color: var(--ink-soft); font-size: 15px; margin-top: 12px;">
              Like Platt's "fit", this isn't the diagonal — it's the best monotone
              step function under squared loss on the calibration set. With enough
              data it gets very close. With too little data, every wiggle is a step
              the algorithm just made up.
            </p>
          </div>
        </div>
        <div class="sticky">
          <IsotonicSteps
            steps={calibrated.isotonic.steps}
            probe={isoProbeByStep}
            maxKnots={isoKnotsByStep} />
        </div>
      </div>
    {/if}

    <h3>C. Brier score, before and after</h3>
    <p class="col">
      <em class="term">Brier score</em> is a proper scoring rule:
      <Tex tex={'\\mathrm{Brier} = \\tfrac{1}{N}\\sum_{i=1}^{N}(\\hat{p}_i - y_i)^2'} />. Unlike accuracy, it penalises both
      direction and magnitude of probabilistic disagreement, so it drops when scores
      become more honest, not just more discriminating.
    </p>

    {#if calibrated && metrics}
      <div class="stats col-wide">
        <div class="stat">
          <div class="label">Raw over-confident</div>
          <div class="value">{calibrated.raw.brier.toFixed(4)}</div>
          <div class="delta">ECE {calibrated.raw.ece.toFixed(3)}</div>
        </div>
        <div class="stat">
          <div class="label">+ Platt scaling</div>
          <div class="value">{calibrated.platt.brier.toFixed(4)}</div>
          <div class="delta">ECE {calibrated.platt.ece.toFixed(3)}</div>
        </div>
        <div class="stat">
          <div class="label">+ Isotonic</div>
          <div class="value">{calibrated.isotonic.brier.toFixed(4)}</div>
          <div class="delta">ECE {calibrated.isotonic.ece.toFixed(3)}</div>
        </div>
      </div>
    {/if}

    <h3>D. Side by side</h3>
    <p class="col">
      Three reliability diagrams stacked on the same axes — raw, after Platt, after
      isotonic. Both calibrators pull the curve back toward the diagonal; isotonic
      lands a touch closer because it doesn't have to be a sigmoid.
    </p>
    {#if part3Reliability.length}
      <div
        class="col-wide"
        use:inView={{ onEnter: startCycle, onExit: stopCycle, threshold: 0.25, rootMargin: '0px' }}>
        <div class="pill-row">
          {#each [
            { id: null, label: 'all' },
            { id: 'raw', label: 'raw', color: palette.raw },
            { id: 'platt', label: 'Platt', color: palette.platt },
            { id: 'isotonic', label: 'isotonic', color: palette.isotonic }
          ] as opt}
            <button
              class="pill"
              class:active={part3Active === opt.id}
              onclick={() => { part3Cycle = false; part3Active = opt.id; }}>
              {#if opt.color}
                <span class="pill-dot" style:background={opt.color}></span>
              {/if}
              {opt.label}
            </button>
          {/each}
        </div>
        <ReliabilityDiagram
          series={part3Reliability}
          activeId={part3Active}
          title="Calibrated vs. raw — over-confident model"
          subtitle="Same model, different score-to-probability maps" />
      </div>
    {/if}

    <p class="col take" use:revealOnView>
      <strong>Takeaway.</strong> Calibration is cheap. Platt is two parameters and
      always tame. Isotonic is more flexible and almost always wins given enough data,
      at the cost of step-function artefacts. Both leave your model's decisions
      unchanged — they just stop the scores from lying.
    </p>
  </section>

  <section class="part">
    <div class="part-intro reveal" use:revealOnView>
      <p class="part-tag">Outro</p>
      <h2 class="title-card">Where this <span class="accent">leaves you</span></h2>
      <p class="part-blurb">
        A score is not a probability until you've earned it.
      </p>
    </div>
    <p class="col reveal" use:revealOnView>
      Train the model the way you always do, then sanity-check its calibration on a
      held-out set; if the curve bends away from the diagonal, fit Platt or isotonic
      on top before you let the score touch any decision boundary other than the
      ranking one.
    </p>
    <p class="col reveal" use:revealOnView>
      Threshold-picking — choosing where to cut for the precision/recall trade-off you
      actually want — is a related-but-separate art, and one we'll come back to in a
      later piece.
    </p>
    <section class="refs col reveal" use:revealOnView aria-labelledby="refs-heading">
      <h3 id="refs-heading">Further reading</h3>
      <ul>
        <li>
          Edgar Ruiz —
          <a href="https://ploomber.io/blog/calibration-curve/" target="_blank" rel="noreferrer">
            How to read a calibration curve (Ploomber blog)</a>.
          A practitioner's tour of reliability diagrams.
        </li>
        <li>
          scikit-learn user guide —
          <a href="https://scikit-learn.org/stable/modules/calibration.html" target="_blank" rel="noreferrer">
            Probability calibration</a>
          (and the
          <a href="https://scikit-learn.org/stable/modules/calibration.html#calibrating-a-classifier" target="_blank" rel="noreferrer">
            "calibrating a classifier"</a>
          subsection). Authoritative reference for Platt + isotonic in code.
        </li>
        <li>
          David Rosenberg —
          <a href="https://davidrosenberg.github.io/ttml2021/calibration/2.calibration.pdf" target="_blank" rel="noreferrer">
            Calibration lecture notes (NYU TTML 2021, PDF)</a>.
          Tight, math-forward treatment of the same ideas.
        </li>
        <li>
          Google ML Crash Course —
          <a href="https://developers.google.com/machine-learning/crash-course/classification/prediction-bias" target="_blank" rel="noreferrer">
            Prediction bias</a>.
          The intuition for why average prediction should match average outcome.
        </li>
        <li>
          Niculescu-Mizil &amp; Caruana (ICML 2005) —
          <a href="https://www.cs.cornell.edu/~alexn/papers/calibration.icml05.crc.rev3.pdf" target="_blank" rel="noreferrer">
            Predicting Good Probabilities With Supervised Learning (PDF)</a>.
          The empirical paper that put Platt vs. isotonic on the map.
        </li>
      </ul>
    </section>

    <p class="col credits" style="color: var(--ink-soft); font-size: 14px;">
      Made with d3 + Svelte + scikit-learn. Code and notebooks in the
      <a href="https://github.com/rexarski/probably-not-probabilities" target="_blank" rel="noreferrer">repository</a>.
    </p>
  </section>
</main>

<style>
  .hero {
    min-height: calc(100vh - 64px);
    padding: 0 0 32px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    scroll-snap-align: start;
    position: relative;
    overflow: hidden;
  }
  .hero > :global(*:not(.mosaic)) {
    position: relative;
    z-index: 1;
  }
  .scroll-cue {
    position: absolute;
    left: 0;
    bottom: 24px;
    font-family: var(--sans);
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ink-soft);
    display: flex;
    align-items: center;
    gap: 10px;
    animation: cue 2.4s ease-in-out infinite;
  }
  .scroll-cue::after {
    content: '';
    width: 1px;
    height: 28px;
    background: linear-gradient(var(--green-soft), transparent);
  }
  @keyframes cue {
    0%, 100% { transform: translateY(0); opacity: 0.55; }
    50% { transform: translateY(6px); opacity: 1; }
  }
  .part-1 {
    scroll-snap-align: start;
    scroll-margin-top: 24px;
  }
  .kicker {
    font-family: var(--sans);
    font-size: 12px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--green-soft);
    margin: 0 0 16px;
  }
  .lede {
    font-size: 20px;
    line-height: 1.55;
    color: var(--ink);
  }
  .part-tag {
    font-family: var(--mono);
    font-size: 11px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--green-soft);
    margin: 0;
  }
  .part {
    margin-top: 128px;
  }
  .rows-figure {
    margin: 36px 0 12px;
  }
  .caption {
    font-family: var(--sans);
    font-size: 12px;
    color: var(--ink-soft);
    margin-top: 12px;
    max-width: var(--col-text);
  }
  .ece-grid {
    display: flex;
    gap: 12px;
    margin-top: 14px;
    flex-wrap: wrap;
    width: 100%;
    justify-content: space-between;
    font-family: var(--sans);
  }
  .ece {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 15px;
    padding: 8px 12px;
    border-radius: 6px;
    border: 1px solid var(--rule);
    color: var(--ink-soft);
    transition: all 0.3s;
  }
  .ece.active {
    color: var(--ink);
    background: rgba(255, 255, 255, 0.03);
    border-color: var(--ink-soft);
  }
  .ece-dot {
    width: 12px;
    height: 12px;
    border-radius: 99px;
  }
  .ece-l {
    font-size: 14px;
  }
  .ece-v {
    font-family: var(--mono);
    font-weight: 600;
    font-size: 15px;
    color: inherit;
    font-feature-settings: 'tnum' 1, 'zero' 1;
  }
  /* Used by Part 2 to align the histogram with the body column and let the
     stats/confusion panels share the sidenote gutter. */
  .figure-grid {
    display: grid;
    grid-template-columns: minmax(0, var(--col-text)) var(--col-side);
    column-gap: var(--col-gap);
    align-items: start;
    margin: 28px 0;
  }
  @media (max-width: 980px) {
    .figure-grid {
      grid-template-columns: 1fr;
    }
  }
  .confusion {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr;
    gap: 4px;
    font-family: var(--sans);
    border: 1px solid var(--rule);
    border-radius: 6px;
    overflow: hidden;
    max-width: 640px;
  }
  .cm {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: var(--bg-alt);
  }
  .cm span {
    color: var(--ink-soft);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .cm b {
    font-family: var(--mono);
    font-size: 18px;
    color: var(--ink);
  }
  .cm-tp b {
    color: var(--green-soft);
  }
  .cm-fp b {
    color: var(--orange);
  }
  .cm-fn b {
    color: var(--orange);
  }
  .take {
    background: var(--bg-alt);
    border-left: 3px solid var(--green);
    padding: 18px 22px;
    margin-top: 36px;
    font-size: 17px;
  }
  .pill-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 99px;
    margin-right: 6px;
    vertical-align: middle;
  }
  .refs {
    margin-top: 56px;
    padding-top: 24px;
    border-top: 1px solid var(--rule);
  }
  .refs h3 {
    font-size: 14px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--green-soft);
    margin: 0 0 16px;
  }
  .refs ul {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    gap: 14px;
  }
  .refs li {
    font-size: 15px;
    line-height: 1.55;
    color: var(--ink-soft);
  }
  .refs a {
    color: var(--ink);
  }
  .credits {
    margin-top: 32px;
  }
</style>
