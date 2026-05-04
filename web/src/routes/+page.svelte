<script>
    import { onMount } from "svelte";
    import {
        loadHoldout,
        loadReliability,
        loadMetrics,
        loadCalibrated,
        loadSampleRows,
    } from "$lib/data.js";
    import { palette } from "$lib/theme.js";
    import { inView, revealOnView } from "$lib/scrollytelling.js";

    import HeroMosaic from "$lib/HeroMosaic.svelte";
    import ReliabilityDiagram from "$lib/charts/ReliabilityDiagram.svelte";
    import ScoreHistogram from "$lib/charts/ScoreHistogram.svelte";
    import GapBars from "$lib/charts/GapBars.svelte";
    import PlattCurve from "$lib/charts/PlattCurve.svelte";
    import IsotonicSteps from "$lib/charts/IsotonicSteps.svelte";
    import SampleRows from "$lib/charts/SampleRows.svelte";
    import RocCurves from "$lib/charts/RocCurves.svelte";
    import CountUp from "$lib/CountUp.svelte";
    import StepDots from "$lib/StepDots.svelte";
    import IdentityReveal from "$lib/IdentityReveal.svelte";
    import Tex from "$lib/Math.svelte";

    /** @type {any} */ let holdout = $state(null);
    /** @type {any} */ let reliability = $state(null);
    /** @type {any} */ let metrics = $state(null);
    /** @type {any} */ let calibrated = $state(null);
    /** @type {any[]} */ let sampleRows = $state([]);

    // Section labels for the A/B/C presentation in Part 1. The internal model
    // ids stay the same (well_calibrated / over_confident / under_confident)
    // so the data joins are unchanged; only what the reader sees is masked.
    const MODEL_LETTER = {
        well_calibrated: "A",
        over_confident: "B",
        under_confident: "C",
    };
    const MODEL_COLOR = {
        well_calibrated: palette.wellCalibrated,
        over_confident: palette.overConfident,
        under_confident: palette.underConfident,
    };

    // ----- Part 1 (was Part 2) state -----
    let modelChoice = $state("over_confident"); // 'well_calibrated' | 'over_confident' | 'under_confident'
    let threshold = $state(0.5);

    // ----- Part 2 (was Part 1) state -----
    let part2Step = $state(0); // 0 = sample rows, 1 = well, 2 = over, 3 = under, 4 = ECE
    let visibleRows = $state(0);

    // ----- Part 3 state -----
    let plattStep = $state(0); // 0 = pre-view, 1 = identity, 2 = steepness only, 3 = MLE fit
    let isoStep = $state(0); // 0 = pre-view, 1 = coarse, 2 = mid, 3 = full
    let calibMethod = $state("platt"); // 'raw' | 'platt' | 'isotonic'

    const plattAByStep = $derived.by(() => {
        const fitted = calibrated?.platt?.params?.a ?? 2.9;
        switch (plattStep) {
            case 0:
                return 1;
            case 1:
                return 1;
            case 2:
                return 5;
            default:
                return fitted;
        }
    });
    const plattBByStep = $derived.by(() => {
        const fitted = calibrated?.platt?.params?.b ?? -1.5;
        switch (plattStep) {
            case 0:
                return 0;
            case 1:
                return 0;
            case 2:
                return 0;
            default:
                return fitted;
        }
    });

    const isoKnotsByStep = $derived.by(() => {
        switch (isoStep) {
            case 0:
                return 5;
            case 1:
                return 5;
            case 2:
                return 16;
            default:
                return 0;
        }
    });
    const isoProbeByStep = $derived(
        isoStep >= 3 ? 0.7 : isoStep === 2 ? 0.55 : 0.4,
    );

    // ----- Section nav state -----
    let activeSection = $state("hero");

    onMount(async () => {
        [holdout, reliability, metrics, calibrated, sampleRows] =
            await Promise.all([
                loadHoldout(),
                loadReliability(),
                loadMetrics(),
                loadCalibrated(),
                loadSampleRows(),
            ]);

        const ids = ["part-1", "part-2", "part-3", "outro"];
        const targets = ids
            .map((id) => document.getElementById(id))
            .filter((el) => el);
        const io = new IntersectionObserver(
            (entries) => {
                for (const e of entries) {
                    if (e.isIntersecting) activeSection = e.target.id;
                }
            },
            { rootMargin: "-35% 0px -55% 0px", threshold: 0 },
        );
        targets.forEach((t) => io.observe(t));
        return () => io.disconnect();
    });

    // Sample-row cycling — same as before, just renamed to part2.
    let rowTimer;
    let rowsInView = $state(false);
    let rowAnimDone = $state(false);

    function tickRowAnim() {
        if (rowTimer || rowAnimDone || !rowsInView || !sampleRows.length)
            return;
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
        if (sampleRows.length && rowsInView) tickRowAnim();
    });

    // ----- Reliability series for Part 2 (filtered by step) -----
    const seriesAll = $derived.by(() => {
        if (!reliability) return [];
        return [
            {
                id: "well_calibrated",
                label: "Well-calibrated",
                color: palette.wellCalibrated,
                points: reliability.well_calibrated,
            },
            {
                id: "over_confident",
                label: "Over-confident",
                color: palette.overConfident,
                points: reliability.over_confident,
            },
            {
                id: "under_confident",
                label: "Under-confident",
                color: palette.underConfident,
                points: reliability.under_confident,
            },
        ];
    });

    const part2Active = $derived(
        part2Step === 1
            ? "well_calibrated"
            : part2Step === 2
              ? "over_confident"
              : part2Step === 3
                ? "under_confident"
                : null,
    );

    // ----- Part 1 derived (histogram + threshold + ROC) -----
    const part1Model = $derived(metrics?.models?.[modelChoice]);
    const part1Reliability = $derived(reliability?.[modelChoice] ?? []);
    const part1Color = $derived(MODEL_COLOR[modelChoice]);

    // Decision counts at current threshold from raw scores
    const decisionStats = $derived.by(() => {
        if (!holdout) return null;
        const arr =
            modelChoice === "well_calibrated"
                ? holdout.p_base
                : modelChoice === "over_confident"
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
        return { tp, fp, tn, fn, precision, recall, n: arr.length };
    });

    // ROC + AUC for each model. Computed once when holdout arrives.
    // Because over/under-confident are monotone transforms of the baseline
    // scores, ranking is preserved and the three ROC curves are essentially
    // identical — that is the pedagogical point.
    function computeRoc(y, scores) {
        const n = scores.length;
        const idx = new Array(n);
        for (let i = 0; i < n; i++) idx[i] = i;
        idx.sort((a, b) => scores[b] - scores[a]);
        let P = 0;
        for (let i = 0; i < n; i++) if (y[i] === 1) P++;
        const N = n - P;
        if (P === 0 || N === 0)
            return {
                points: [
                    { fpr: 0, tpr: 0 },
                    { fpr: 1, tpr: 1 },
                ],
                auc: 0.5,
            };
        const points = [{ fpr: 0, tpr: 0 }];
        let tp = 0,
            fp = 0;
        let prev = Infinity;
        let auc = 0;
        let lastFpr = 0,
            lastTpr = 0;
        for (let k = 0; k < n; k++) {
            const i = idx[k];
            const s = scores[i];
            if (s !== prev) {
                const fpr = fp / N,
                    tpr = tp / P;
                if (k > 0) {
                    points.push({ fpr, tpr });
                    auc += ((fpr - lastFpr) * (tpr + lastTpr)) / 2;
                    lastFpr = fpr;
                    lastTpr = tpr;
                }
                prev = s;
            }
            if (y[i] === 1) tp++;
            else fp++;
        }
        const fpr = fp / N,
            tpr = tp / P;
        points.push({ fpr, tpr });
        auc += ((fpr - lastFpr) * (tpr + lastTpr)) / 2;
        // Downsample for SVG path efficiency — the curves can have thousands of
        // breakpoints; ~600 is plenty for a smooth render at this size.
        const target = 600;
        if (points.length <= target) return { points, auc };
        const step = Math.ceil(points.length / target);
        const sampled = [];
        for (let i = 0; i < points.length; i += step) sampled.push(points[i]);
        if (sampled[sampled.length - 1] !== points[points.length - 1])
            sampled.push(points[points.length - 1]);
        return { points: sampled, auc };
    }

    const rocSeries = $derived.by(() => {
        if (!holdout) return [];
        const a = computeRoc(holdout.y_true, holdout.p_base);
        const b = computeRoc(holdout.y_true, holdout.p_over);
        const c = computeRoc(holdout.y_true, holdout.p_under);
        return [
            {
                id: "well_calibrated",
                label: "Model A",
                color: palette.wellCalibrated,
                points: a.points,
                auc: a.auc,
            },
            {
                id: "over_confident",
                label: "Model B",
                color: palette.overConfident,
                points: b.points,
                auc: b.auc,
            },
            {
                id: "under_confident",
                label: "Model C",
                color: palette.underConfident,
                points: c.points,
                auc: c.auc,
            },
        ];
    });

    // ----- Part 3 derived -----
    let part3Active = $state(
        /** @type {null | 'raw' | 'platt' | 'isotonic'} */ (null),
    );
    let part3Cycle = $state(false);
    const part3Reliability = $derived.by(() => {
        if (!calibrated) return [];
        return [
            {
                id: "raw",
                label: "Raw (over-confident)",
                color: palette.raw,
                points: calibrated.raw.reliability,
            },
            {
                id: "platt",
                label: "After Platt",
                color: palette.platt,
                points: calibrated.platt.reliability,
            },
            {
                id: "isotonic",
                label: "After isotonic",
                color: palette.isotonic,
                points: calibrated.isotonic.reliability,
            },
        ];
    });

    let cycleTimer;
    $effect(() => {
        if (part3Cycle) {
            const order = ["raw", "platt", "isotonic"];
            let i = 0;
            part3Active = order[i];
            cycleTimer = setInterval(() => {
                i = (i + 1) % order.length;
                part3Active = order[i];
            }, 1800);
            return () => clearInterval(cycleTimer);
        }
    });
    function startCycle() {
        if (part3Active === null) part3Cycle = true;
    }
    function stopCycle() {
        part3Cycle = false;
    }
</script>

<svelte:head>
    <title>Probably Not Probabilities — a calibration walk-through</title>
</svelte:head>

<!-- ============================== TIMELINE NAV ============================== -->
<aside class="toc" aria-label="Article sections">
    <ul>
        <li class:active={activeSection === "part-1"}>
            <a href="#part-1"
                ><span class="num">01</span><span class="lab"
                    >Performance ≠ decisions</span
                ></a
            >
        </li>
        <li class:active={activeSection === "part-2"}>
            <a href="#part-2"
                ><span class="num">02</span><span class="lab"
                    >What is calibration</span
                ></a
            >
        </li>
        <li class:active={activeSection === "part-3"}>
            <a href="#part-3"
                ><span class="num">03</span><span class="lab"
                    >How to calibrate</span
                ></a
            >
        </li>
        <li class:active={activeSection === "outro"}>
            <a href="#outro"
                ><span class="num">04</span><span class="lab"
                    >Where it leaves you</span
                ></a
            >
        </li>
    </ul>
</aside>

<main class="page">
    <!-- ============================== HERO ============================== -->
    <header class="hero" id="hero">
        <HeroMosaic />
        <p class="kicker">On probability calibration</p>
        <h1>
            Probably <span class="green">Not</span><br />
            Probabilities
        </h1>
        <p class="lede col">
            Classification models hand you a number between zero and one. It
            looks like a probability. It quacks like a probability. We treat it
            like a probability — set a threshold at <code>0.5</code>, ship the
            decision, move on. But that number is really only a
            <em class="term">score</em>. Whether it behaves like a true
            probability is a separate question entirely. That question is called
            <em class="term">calibration</em>, and it's what this piece is
            about.
        </p>
        <p class="lede col" style="color: var(--ink-soft); font-size: 16px;">
            We trained two flavors of a hit-song classifier on
            <a
                href="https://www.kaggle.com/datasets/maharshipandya/-spotify-tracks-dataset"
                target="_blank"
                rel="noreferrer">114k Spotify tracks</a
            >
            — one made over-confident, one under-confident — to see what miscalibration
            actually looks like, why it ruins downstream decisions, and how two classic
            tricks (Platt scaling and isotonic regression) repair it.
        </p>
        <div class="scroll-cue" aria-hidden="true">scroll</div>
    </header>

    <!-- ============================== PART 1 (was Part 2): WHY IT MATTERS ============================== -->
    <section class="part part-1" id="part-1">
        <div class="part-intro reveal" use:revealOnView>
            <p class="part-tag">Part&nbsp;1</p>
            <h2 class="title-card">
                High model performance does not guarantee
                <span class="accent">correct decisions</span>
            </h2>
            <p class="part-blurb">
                Three classifiers — call them <strong>A</strong>,
                <strong>B</strong>, and
                <strong>C</strong> — that rank tracks identically and post the same
                headline AUC. The moment a threshold is drawn, they part ways.
            </p>
        </div>

        <div class="with-sidenote reveal" use:revealOnView>
            <div class="col">
                <p>
                    We have three different models that all stack tracks in the
                    same order. By any ranking-only metric — AUC, average
                    precision — they're indistinguishable. But ranking is the
                    easy half. Decisions aren't. The moment you compare a score
                    to a threshold — to send a song to a "promote" queue, to
                    alert a doctor, to flag a transaction — you're treating that
                    score as if it meant something. And there, the three models
                    fall apart.
                </p>
            </div>
            <aside class="sidenote">
                Threshold 0.5 is convention, not law. The right cutoff depends
                on the cost ratio between false positives and false negatives —
                and on whether the score you're cutting against is a probability
                in the first place.
            </aside>
        </div>

        <div class="pill-row col">
            {#each [{ id: "well_calibrated", label: "Model A" }, { id: "over_confident", label: "Model B" }, { id: "under_confident", label: "Model C" }] as opt}
                <button
                    class="pill"
                    class:active={modelChoice === opt.id}
                    onclick={() => (modelChoice = opt.id)}
                >
                    <span
                        class="pill-dot"
                        style:background={MODEL_COLOR[opt.id]}
                    ></span>
                    {opt.label}
                </button>
            {/each}
        </div>

        <p class="col">
            Drag the <em>threshold</em> below — or click anywhere on the histogram
            — to see what changes when you decide a different point is "promote-worthy".
            The ROC panel on the right shows ranking quality for all three models;
            the histogram shows how each one distributes its scores.
        </p>

        {#if part1Model && decisionStats}
            <div class="figure-grid col-wide">
                <ScoreHistogram
                    bins={part1Model.histogram}
                    {threshold}
                    color={part1Color}
                    onThreshold={(t) => (threshold = t)}
                    title="Score distribution — Model {MODEL_LETTER[
                        modelChoice
                    ]}"
                    subtitle="Click or drag to pick a threshold"
                />

                <div class="roc-wrap">
                    {#if rocSeries.length}
                        <RocCurves
                            series={rocSeries}
                            activeId={modelChoice}
                            title="ROC — ranking quality"
                            subtitle="Three curves, one path → identical AUC"
                        />
                    {/if}
                    <p class="roc-caption">
                        Same ranks, same AUC. AUC sees only order, so it can't
                        tell A, B, and C apart — even though they will make very
                        different decisions below.
                    </p>
                </div>

                <div class="stat-row">
                    <div class="stat">
                        <div class="label">Threshold</div>
                        <div class="value">{threshold.toFixed(2)}</div>
                    </div>
                    <div class="stat">
                        <div class="label">Precision</div>
                        <div class="value">
                            <CountUp
                                value={decisionStats.precision * 100}
                                format={(v) => `${v.toFixed(1)}%`}
                            />
                        </div>
                        <div class="delta">tp / (tp + fp)</div>
                    </div>
                    <div class="stat">
                        <div class="label">Recall</div>
                        <div class="value">
                            <CountUp
                                value={decisionStats.recall * 100}
                                format={(v) => `${v.toFixed(1)}%`}
                            />
                        </div>
                        <div class="delta">tp / (tp + fn)</div>
                    </div>
                </div>

                <div class="confusion">
                    <div class="cm cm-tp">
                        <span>true positives</span><b
                            ><CountUp
                                value={decisionStats.tp}
                                format={(v) => Math.round(v).toLocaleString()}
                            /></b
                        >
                    </div>
                    <div class="cm cm-fp">
                        <span>false positives</span><b
                            ><CountUp
                                value={decisionStats.fp}
                                format={(v) => Math.round(v).toLocaleString()}
                            /></b
                        >
                    </div>
                    <div class="cm cm-fn">
                        <span>false negatives</span><b
                            ><CountUp
                                value={decisionStats.fn}
                                format={(v) => Math.round(v).toLocaleString()}
                            /></b
                        >
                    </div>
                    <div class="cm cm-tn">
                        <span>true negatives</span><b
                            ><CountUp
                                value={decisionStats.tn}
                                format={(v) => Math.round(v).toLocaleString()}
                            /></b
                        >
                    </div>
                </div>

                <p class="col" style="grid-column: 1 / -1; margin-top: 12px;">
                    Watch what each model does as you slide the threshold. <strong
                        class="mt mt-b">Model B</strong
                    >
                    piles almost everything past 0.9 or below 0.1, so the threshold
                    barely moves the count of "yes" decisions until it crosses that
                    wall. <strong class="mt mt-c">Model C</strong>
                    is the opposite: every threshold inside [0.3, 0.7] reshuffles
                    thousands of tracks.
                    <strong class="mt mt-a">Model A</strong> sits between them, its
                    scores spread evenly. Same ranking; very different operating curves.
                </p>

                <GapBars
                    points={part1Reliability}
                    color={part1Color}
                    title="Predicted score vs. actual hit rate, per bin"
                    subtitle="Bars: mean predicted score in the bin. Black rule: actual hit rate. The gap is the model's miss."
                />
            </div>
        {/if}

        <p class="col take" use:revealOnView>
            <strong>Takeaway.</strong> When predicted scores are used to
            <em>make decisions</em>
            — thresholds, risk scoring, expected-value math, resource allocation —
            ranking quality is not enough. AUC suggests everything is fine right up
            until the point your thresholds start lying. Whatever is going on inside
            the score itself is what the rest of this piece is about.
        </p>
    </section>

    <!-- ============================== PART 2 (was Part 1): WHAT IS CALIBRATION ============================== -->
    <section class="part part-2" id="part-2">
        <div class="part-intro reveal" use:revealOnView>
            <p class="part-tag">Part&nbsp;2</p>
            <h2 class="title-card">
                What is <span class="accent">calibration</span>?
            </h2>
            <p class="part-blurb">
                Time to lift the curtain on A, B, and C — and to put a name on
                the property that makes their scores so different.
            </p>
        </div>

        <div class="col">
            <IdentityReveal />
        </div>

        <div class="with-sidenote reveal" use:revealOnView>
            <div class="col">
                <p>
                    The reason A, B, and C made the same ranking but very
                    different decisions is a property of the score itself,
                    called <em class="term">calibration</em>. From now on we can
                    drop the placeholder names:
                    <strong class="mt mt-a">Model A</strong>
                    is
                    <em>well-calibrated</em>,
                    <strong class="mt mt-b">Model B</strong>
                    is <em>over-confident</em>, and
                    <strong class="mt mt-c">Model C</strong>
                    is <em>under-confident</em>. They share a ranking because B
                    and C are built from A's score by a monotone transform —
                    squashing out toward 0 / 1 (B) or pulling in toward 0.5 (C).
                    The order is preserved; the meaning of the number is not.
                </p>
                <p>
                    Formally, a classifier <code>f</code> is
                    <em class="term">calibrated</em>
                    when, among all the cases it rates around <code>p</code>,
                    roughly a
                    <code>p</code>-fraction are actually positive. So among
                    songs the model labels with score 0.7, about 70&nbsp;%
                    really are popular hits.
                </p>
                <Tex
                    display
                    tex={"\\Pr\\bigl[\\,Y=1 \\,\\big|\\, f(X)=p\\,\\bigr] \\;=\\; p \\quad \\forall\\, p \\in [0,1]."}
                />
            </div>
            <aside class="sidenote">
                Calibration is a property of the score, not of the prediction.
                Accuracy and ranking quality are different properties — a model
                can be perfectly accurate yet badly calibrated, and vice-versa.
            </aside>
        </div>

        <p class="col">
            The two squashed models make almost the same <em>decisions</em> at
            threshold 0.5 as the well-calibrated one — they're roughly tied on
            accuracy. But their
            <em>scores</em> tell completely different stories. Watch how an over-confident
            model crowds tracks toward 0&nbsp;and 1, while an under-confident one
            keeps everything bunched around the middle.
        </p>

        {#if sampleRows.length}
            <div
                class="rows-figure col-wide"
                use:inView={{
                    onEnter: startRowAnim,
                    onExit: stopRowAnim,
                    threshold: 0.15,
                    rootMargin: "0px",
                }}
            >
                <SampleRows rows={sampleRows} visibleCount={visibleRows} />
                <p class="caption">
                    Six tracks from the holdout set. Both models score them —
                    yet one is theatrical and the other is timid. The decision
                    at <code>t = 0.5</code> is the same in many rows, even when the
                    score moves from 0.05 to 0.85.
                </p>
            </div>
        {/if}

        <h3 style="margin-top: 100px;">The reliability diagram</h3>
        <p class="col">
            To <em>see</em> calibration, we plot predicted score against the actual
            fraction of hits in each score bin. A perfect model traces the diagonal.
            Anything else tells you, at a glance, where the model is over- or under-shooting.
        </p>

        <div class="col axis-key">
            <p>
                Read each point on the diagram as one bucket of tracks. Sort the
                holdout by score, slice it into bins, then look at two numbers
                per bin: the model's mean score (the <em>x</em>-axis) versus the
                actual hit rate inside that bin (the
                <em>y</em>-axis). If they agree, the bin lands on the diagonal.
            </p>
            <table class="key-table">
                <thead>
                    <tr>
                        <th>Bin (score range)</th>
                        <th>Tracks</th>
                        <th>Mean predicted <span>x</span></th>
                        <th>Actual hit rate <span>y</span></th>
                        <th>Reads as</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><code>0.55 – 0.65</code></td>
                        <td>1,830</td>
                        <td>0.61</td>
                        <td>0.58</td>
                        <td
                            ><span class="ok">close to diagonal — honest</span
                            ></td
                        >
                    </tr>
                    <tr>
                        <td><code>0.85 – 0.95</code></td>
                        <td>1,210</td>
                        <td>0.91</td>
                        <td>0.74</td>
                        <td
                            ><span class="bad"
                                >below diagonal — over-confident</span
                            ></td
                        >
                    </tr>
                </tbody>
            </table>
            <p class="key-caption">
                The two rows above are the same axes the chart on the right uses
                — same bins, same numbers, just plotted as <code>(x, y)</code> coordinates
                instead of cells.
            </p>
        </div>

        <div class="scrolly">
            <div class="steps">
                <div
                    class="step reveal-step"
                    class:active={part2Step === 1}
                    use:revealOnView
                    use:inView={{
                        onEnter: () => (part2Step = 1),
                        threshold: 0.6,
                    }}
                >
                    <h3>Well-calibrated (Model A)</h3>
                    <p>
                        The well-trained gradient boosting model hugs the
                        diagonal. When it says
                        <code>0.6</code>, about 60&nbsp;% of those tracks really
                        are popular. Its
                        <em class="term">expected calibration error</em> on the holdout
                        set is small.
                    </p>
                </div>
                <div
                    class="step reveal-step"
                    class:active={part2Step === 2}
                    use:revealOnView
                    use:inView={{
                        onEnter: () => (part2Step = 2),
                        threshold: 0.6,
                    }}
                >
                    <h3>Over-confident (Model B)</h3>
                    <p>
                        We squash this model's logits outward, so its scores
                        live near 0 and 1. It's still right at threshold 0.5 —
                        but when it says <code>0.95</code>, the actual hit rate
                        is closer to <code>0.7</code>. The curve drops below the
                        diagonal at the top, climbs above it at the bottom.
                    </p>
                </div>
                <div
                    class="step reveal-step"
                    class:active={part2Step === 3}
                    use:revealOnView
                    use:inView={{
                        onEnter: () => (part2Step = 3),
                        threshold: 0.6,
                    }}
                >
                    <h3>Under-confident (Model C)</h3>
                    <p>
                        The opposite move pulls scores toward <code>0.5</code>.
                        The model never commits. When it whispers
                        <code>0.55</code>, the actual hit rate is more like
                        <code>0.7</code>. Below 0.5, it's similarly too shy.
                    </p>
                </div>
                <div
                    class="step reveal-step"
                    class:active={part2Step === 4}
                    use:revealOnView
                    use:inView={{
                        onEnter: () => (part2Step = 4),
                        threshold: 0.6,
                    }}
                >
                    <h3>Two metrics, two emphases</h3>
                    <p>
                        <em class="term">Expected Calibration Error</em> (ECE)
                        bins the predictions and averages the absolute gap
                        between mean predicted score and observed hit rate,
                        weighted by bin size. It's a measure of <em>bias</em> — how
                        far the curve drifts from the diagonal, on average.
                    </p>
                    <Tex
                        display
                        tex={"\\mathrm{ECE} \\;=\\; \\sum_{b=1}^{B} \\frac{n_b}{N}\\,\\bigl|\\,\\overline{p}_b \\;-\\; \\overline{y}_b\\,\\bigr|"}
                    />
                    <p>
                        <em class="term">Brier score</em> is a per-prediction
                        squared error against the label. Unlike ECE, it doesn't
                        bin — and unlike accuracy, it punishes the
                        <em>distance</em> of a wrong probability, not just the wrong
                        side of a threshold. So Brier drops with both better calibration
                        and sharper, more decisive scores.
                    </p>
                    <Tex
                        display
                        tex={"\\mathrm{Brier} \\;=\\; \\frac{1}{N}\\sum_{i=1}^{N}\\bigl(\\hat{p}_i - y_i\\bigr)^2"}
                    />
                </div>
            </div>
            <div class="sticky">
                {#if reliability}
                    <ReliabilityDiagram
                        series={seriesAll}
                        activeId={part2Active}
                        annotations={part2Step >= 4 && metrics?.models
                            ? {
                                  well_calibrated:
                                      metrics.models.well_calibrated.ece,
                                  over_confident:
                                      metrics.models.over_confident.ece,
                                  under_confident:
                                      metrics.models.under_confident.ece,
                              }
                            : null}
                        title="Reliability diagram — three flavors"
                        subtitle="x: mean predicted score per bin · y: actual fraction of hits · circles sized by bin count"
                    />
                {/if}
            </div>
        </div>

        <h3>Why does the gap appear at all?</h3>
        <p class="col">
            Most learners optimize <em>discriminative</em> losses — cross-entropy,
            hinge, log-loss — that reward putting the right class on the right side
            of the boundary. Calibration isn't part of the objective, so it isn't
            guaranteed to fall out of training. A few common ways the gap creeps in:
        </p>
        <ul class="col reasons">
            <li>
                <strong>High-capacity models</strong> — boosted trees and deep
                nets, fit to convergence, push their outputs toward 0 or 1 to
                drive the loss down. Their sigmoids saturate. Result:
                <em>over-confidence</em>.
            </li>
            <li>
                <strong
                    >Strong regularization, early stopping, or shrinkage</strong
                >
                hold the outputs back from the extremes. Logits stay close to zero,
                scores cluster around 0.5. Result:
                <em>under-confidence</em>.
            </li>
            <li>
                <strong>Class imbalance, resampling, or class weighting</strong> shift
                the prior the model implicitly assumes. The threshold the model would
                have learned drifts away from the true rate.
            </li>
            <li>
                <strong>Distribution shift</strong> at inference time — different
                audience, different period — breaks any calibration the training set
                bought you.
            </li>
        </ul>
        <p class="col">
            None of these are bugs. They're side-effects of optimizing a
            different objective than "honest probabilities". The gap is the
            price you pay; calibration is how you pay it back.
        </p>

        <p class="col take" use:revealOnView>
            <strong>Takeaway.</strong> A calibrated model's scores behave like true
            probabilities. Most out of the box models aren't calibrated -- uncalibrated
            scores beyond ranking is on a shaky ground.
        </p>
    </section>

    <!-- ============================== PART 3 ============================== -->
    <section class="part part-3" id="part-3">
        <div class="part-intro reveal" use:revealOnView>
            <p class="part-tag">Part&nbsp;3</p>
            <h2 class="title-card">
                How to <span class="accent">calibrate</span>
            </h2>
            <p class="part-blurb">
                Two classic post-hoc fixes — Platt scaling and isotonic
                regression.
            </p>
        </div>

        <p class="col reveal" use:revealOnView>
            The good news: you don't need to retrain the model. Calibration is a
            <em class="term">post-hoc</em> step. You take the model's raw scores on
            a held-out slice of data, learn a monotone function that maps those scores
            to actual hit rates, and then apply it at inference time.
        </p>

        <h3>A. Platt scaling</h3>
        <div class="with-sidenote">
            <div class="col">
                <p>
                    Platt scaling fits a one-dimensional logistic regression on
                    top of the model's score:
                </p>
                <Tex
                    display
                    tex={"\\hat{p}(x) \\;=\\; \\sigma\\!\\bigl(a\\cdot s(x) + b\\bigr) \\;=\\; \\frac{1}{1 + e^{-(a\\,s(x) + b)}}"}
                />
                <p>
                    where <code>s(x)</code> is the raw score and
                    <code>a, b</code> are the maximum-likelihood estimates from the
                    calibration set. Two parameters — fast, stable, works with very
                    little data. The drawback: a sigmoid can only undo S-shaped distortions;
                    if the underlying miscalibration has a different shape, Platt
                    won't fully close the gap.
                </p>
            </div>
            <aside class="sidenote">
                Originally proposed by John Platt (1999) to extract
                probabilities from SVM decision values, which by construction
                don't have a probabilistic meaning at all.
            </aside>
        </div>

        <div class="scrolly">
            <div class="steps">
                <div
                    class="step reveal-step"
                    class:active={plattStep === 1}
                    use:revealOnView
                    use:inView={{
                        onEnter: () => (plattStep = 1),
                        threshold: 0.6,
                    }}
                >
                    <h3>Step 1 — A flat sigmoid</h3>
                    <p>
                        Start with <code>a&nbsp;=&nbsp;1, b&nbsp;=&nbsp;0</code
                        >. The map is σ(s) — gentle, almost a straight line over
                        [0, 1]. It barely changes the scores. Useless as a
                        calibrator, but a clear baseline.
                    </p>
                </div>
                <div
                    class="step reveal-step"
                    class:active={plattStep === 2}
                    use:revealOnView
                    use:inView={{
                        onEnter: () => (plattStep = 2),
                        threshold: 0.6,
                    }}
                >
                    <h3>Step 2 — Crank the steepness</h3>
                    <p>
                        Push <code>a</code> up to 5, leave <code>b</code> at 0.
                        Now the curve has slope, but it's anchored at the wrong
                        place — saturating from the left edge, never lingering
                        near the diagonal. <code>b</code> still needs to do its job.
                    </p>
                </div>
                <div
                    class="step reveal-step"
                    class:active={plattStep === 3}
                    use:revealOnView
                    use:inView={{
                        onEnter: () => (plattStep = 3),
                        threshold: 0.6,
                    }}
                >
                    <h3>Step 3 — The MLE fit</h3>
                    <p>
                        Solve for <code>(a, b)</code> that maximize the
                        log-likelihood of the calibration labels. Result:
                        <code>a&nbsp;=&nbsp;{plattAByStep.toFixed(2)}</code>,
                        <code>b&nbsp;=&nbsp;{plattBByStep.toFixed(2)}</code>.
                        <em>This is the fitted Platt scaler.</em>
                    </p>
                    <p
                        style="color: var(--ink-soft); font-size: 15px; margin-top: 12px;"
                    >
                        "Fitted" doesn't mean the curve traces the diagonal
                        exactly — it means
                        <em
                            >those parameters maximize likelihood under the
                            sigmoid family.</em
                        >
                        Any residual bend is an artifact of the family being too restrictive.
                        That's exactly the gap isotonic closes next.
                    </p>
                </div>
            </div>
            <div class="sticky">
                <StepDots
                    active={plattStep}
                    labels={["flat sigmoid", "steepness", "MLE fit"]}
                />
                <PlattCurve a={plattAByStep} b={plattBByStep} />
            </div>
        </div>

        <h3>B. Isotonic regression</h3>
        <div class="with-sidenote">
            <div class="col">
                <p>
                    Isotonic regression drops the parametric assumption. Given
                    pairs
                    <code>(score, label)</code>, it finds the best
                    non-decreasing step function mapping scores to probabilities
                    — solved efficiently by the
                    <em class="term">Pool Adjacent Violators</em> (PAVA) algorithm.
                    More flexible than Platt, but it can overfit on small calibration
                    sets, since each step is essentially a free parameter.
                </p>
                <Tex
                    display
                    tex={"\\min_{f}\\; \\sum_{i=1}^{N}\\bigl(y_i - f(s_i)\\bigr)^2 \\quad \\text{s.t. } f \\text{ non-decreasing}"}
                />
            </div>
            <aside class="sidenote">
                Rule of thumb: Platt for &lt;1k calibration samples, isotonic
                for ≥1k. For very large sets, Bayesian Beta calibration
                sometimes beats both, but it's a smaller-impact win.
            </aside>
        </div>

        {#if calibrated?.isotonic?.steps}
            <div class="scrolly">
                <div class="steps">
                    <div
                        class="step reveal-step"
                        class:active={isoStep === 1}
                        use:revealOnView
                        use:inView={{
                            onEnter: () => (isoStep = 1),
                            threshold: 0.6,
                        }}
                    >
                        <h3>Step 1 — A coarse staircase</h3>
                        <p>
                            Just five knots. The PAVA solution is forced into a
                            few wide plateaus — clearly not flexible enough to
                            track a real distortion, but enough to show what
                            "monotone step function" means.
                        </p>
                    </div>
                    <div
                        class="step reveal-step"
                        class:active={isoStep === 2}
                        use:revealOnView
                        use:inView={{
                            onEnter: () => (isoStep = 2),
                            threshold: 0.6,
                        }}
                    >
                        <h3>Step 2 — More resolution</h3>
                        <p>
                            Sixteen knots. The staircase starts to bend with the
                            data, hugging the diagonal more closely. Every
                            additional knot is a free parameter the algorithm
                            can spend.
                        </p>
                    </div>
                    <div
                        class="step reveal-step"
                        class:active={isoStep === 3}
                        use:revealOnView
                        use:inView={{
                            onEnter: () => (isoStep = 3),
                            threshold: 0.6,
                        }}
                    >
                        <h3>Step 3 — The full PAVA fit</h3>
                        <p>
                            Every unique calibration sample becomes a candidate
                            knot, and PAVA merges adjacent pairs whenever
                            monotonicity is violated. The result is the <em
                                >fitted</em
                            > isotonic regression — non-parametric, no shape assumption
                            beyond "non-decreasing".
                        </p>
                        <p
                            style="color: var(--ink-soft); font-size: 15px; margin-top: 12px;"
                        >
                            Like Platt's "fit", this isn't the diagonal — it's
                            the best monotone step function under squared loss
                            on the calibration set. With enough data it gets
                            very close. With too little data, every wiggle is a
                            step the algorithm just made up.
                        </p>
                    </div>
                </div>
                <div class="sticky">
                    <StepDots
                        active={isoStep}
                        labels={["5 knots", "16 knots", "all knots"]}
                    />
                    <IsotonicSteps
                        steps={calibrated.isotonic.steps}
                        probe={isoProbeByStep}
                        maxKnots={isoKnotsByStep}
                    />
                </div>
            </div>
        {/if}

        <h3>C. Brier score, before and after</h3>
        <p class="col">
            We met Brier score back in Part&nbsp;2 — a proper scoring rule that
            punishes probabilistic distance from the truth, not just the
            threshold-side. Calibration should drop it, and below it does.
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
                    <div class="delta">
                        ECE {calibrated.platt.ece.toFixed(3)}
                    </div>
                </div>
                <div class="stat">
                    <div class="label">+ Isotonic</div>
                    <div class="value">
                        {calibrated.isotonic.brier.toFixed(4)}
                    </div>
                    <div class="delta">
                        ECE {calibrated.isotonic.ece.toFixed(3)}
                    </div>
                </div>
            </div>
        {/if}

        <h3>D. Side by side</h3>
        <p class="col">
            Three reliability diagrams stacked on the same axes — raw, after
            Platt, after isotonic. Both calibrators pull the curve back toward
            the diagonal; isotonic lands a touch closer because it doesn't have
            to be a sigmoid.
        </p>
        {#if part3Reliability.length}
            <div
                class="col-wide"
                use:inView={{
                    onEnter: startCycle,
                    onExit: stopCycle,
                    threshold: 0.25,
                    rootMargin: "0px",
                }}
            >
                <div class="pill-row">
                    {#each [{ id: null, label: "all" }, { id: "raw", label: "raw", color: palette.raw }, { id: "platt", label: "Platt", color: palette.platt }, { id: "isotonic", label: "isotonic", color: palette.isotonic }] as opt}
                        <button
                            class="pill"
                            class:active={part3Active === opt.id}
                            onclick={() => {
                                part3Cycle = false;
                                part3Active = opt.id;
                            }}
                        >
                            {#if opt.color}
                                <span
                                    class="pill-dot"
                                    style:background={opt.color}
                                ></span>
                            {/if}
                            {opt.label}
                        </button>
                    {/each}
                </div>
                <ReliabilityDiagram
                    series={part3Reliability}
                    activeId={part3Active}
                    title="Calibrated vs. raw — over-confident model"
                    subtitle="Same model, different score-to-probability maps"
                />
            </div>
        {/if}

        <h3>E. What about multiclass?</h3>
        <p class="col">
            Everything above is binary: one score, one diagonal. Multiclass
            needs a quick detour — same idea, harder bookkeeping.
        </p>
        <div class="with-sidenote">
            <div class="col">
                <p>
                    A <em class="term">K</em>-class softmax outputs a
                    probability vector on the simplex. "Calibrated" can mean two
                    related-but-distinct things:
                    <em>top-label</em> calibration (when the model says its top
                    guess has confidence 0.7, it's right 70&nbsp;% of the time)
                    and <em>class-wise</em>
                    calibration (the same diagonal property holds for every class
                    separately). The full joint requirement — every probability vector
                    matches its conditional frequency — is much stricter and rarely
                    measured directly.
                </p>
                <p>The practical headaches are:</p>
                <ul class="reasons">
                    <li>
                        <strong>Less data per class.</strong> Reliability bins
                        fragment by class, so a fixed holdout buys you K-times
                        fewer samples per curve. Isotonic, which wanted &gt;1k
                        binary samples, now wants &gt;1k <em>per class</em>.
                    </li>
                    <li>
                        <strong>Normalization drift.</strong> Calibrate each class
                        independently and the K outputs no longer sum to 1. Either
                        renormalize (and lose the per-class fit) or use a method that
                        respects the simplex.
                    </li>
                    <li>
                        <strong>Confounding from class imbalance.</strong> A long
                        tail of rare classes can be wildly miscalibrated without budging
                        top-label ECE, since the headline metric is dominated by the
                        head of the distribution.
                    </li>
                </ul>
                <p>The usual remedies, roughly in order of complexity:</p>
                <ul class="reasons">
                    <li>
                        <strong>One-vs-rest Platt or isotonic.</strong> Fit K binary
                        calibrators, then renormalize. Cheap, often good enough, no
                        joint guarantees.
                    </li>
                    <li>
                        <strong>Temperature scaling.</strong> One scalar
                        <code>T</code>
                        divides the logits before softmax:
                        <code>p_k ∝ exp(z_k / T)</code>. A single parameter, fit
                        by NLL on a holdout. Surprisingly strong baseline for
                        deep nets — the empirical default since
                        <a
                            href="https://arxiv.org/abs/1706.04599"
                            target="_blank"
                            rel="noreferrer">Guo et&nbsp;al. (2017)</a
                        >.
                    </li>
                    <li>
                        <strong>Vector / matrix scaling.</strong> Per-class temperatures
                        (vector) or a full linear map on logits (matrix). More expressive
                        than temperature, but needs more calibration data and can
                        overfit.
                    </li>
                    <li>
                        <strong>Dirichlet calibration.</strong> A
                        multinomial-logistic regression on the log-probability
                        vector — preserves the simplex, generalizes Platt to K
                        classes (<a
                            href="https://arxiv.org/abs/1910.12656"
                            target="_blank"
                            rel="noreferrer">Kull et&nbsp;al., 2019</a
                        >).
                    </li>
                </ul>
            </div>
            <aside class="sidenote">
                Quick rule of thumb: small <code>K</code>, plenty of data →
                one-vs-rest isotonic. Deep neural net, lots of classes, modest
                holdout → temperature scaling is almost always the first thing
                to try.
            </aside>
        </div>

        <p class="col take" use:revealOnView>
            <strong>Takeaway.</strong> Calibration is cheap. Platt is two parameters
            and always tame. Isotonic is more flexible and almost always wins given
            enough data, at the cost of step-function artifacts. Both leave your model's
            decisions unchanged — they just stop the scores from lying.
        </p>
    </section>

    <!-- ============================== OUTRO ============================== -->
    <section class="part" id="outro">
        <div class="part-intro reveal" use:revealOnView>
            <p class="part-tag">Outro</p>
            <h2 class="title-card">
                Where this <span class="accent">leaves you</span>
            </h2>
            <p class="part-blurb">
                A score is not a probability until you've earned it.
            </p>
        </div>
        <p class="col reveal" use:revealOnView>
            One last thing — and an honest one. Calibration is <em>not</em> a compulsory
            step for every classifier. It depends entirely on what you're going to
            do with the output.
        </p>
        <p class="col reveal" use:revealOnView>
            If your model only ever produces an ordered ranking, a top-1 label,
            or a single class id, there's nothing to calibrate. The score never
            leaves the
            <em>argmax</em>; its absolute value never enters a downstream
            calculation. Leave it alone.
        </p>
        <p class="col reveal" use:revealOnView>
            The moment your model emits a floating-point number that any reader
            will
            <em>treat</em> as a probability, the picture changes. Once a score sits
            in a table next to a label, someone will read it as one. They'll say "0.5
            in class A versus 0.25 in class B means A is twice as likely" — and unless
            the model is calibrated, that sentence is a nicely-rendered guess. Two
            scores in a 2:1 ratio do not, in general, mean a 2:1 likelihood ratio.
            They're just two scores in a 2:1 ratio.
        </p>
        <p class="col reveal" use:revealOnView>
            So: if your output is a number that pretends to be a probability,
            calibrate it, or at least audit it. If it isn't, don't bother.
            Feedback is always welcome.
        </p>
        <section
            class="refs col reveal"
            use:revealOnView
            aria-labelledby="refs-heading"
        >
            <h3 id="refs-heading">Further reading</h3>
            <ul>
                <li>
                    Edgar Ruiz —
                    <a
                        href="https://ploomber.io/blog/calibration-curve/"
                        target="_blank"
                        rel="noreferrer"
                    >
                        How to read a calibration curve (Ploomber blog)</a
                    >. A practitioner's tour of reliability diagrams.
                </li>
                <li>
                    scikit-learn user guide —
                    <a
                        href="https://scikit-learn.org/stable/modules/calibration.html"
                        target="_blank"
                        rel="noreferrer"
                    >
                        Probability calibration</a
                    >
                    (and the
                    <a
                        href="https://scikit-learn.org/stable/modules/calibration.html#calibrating-a-classifier"
                        target="_blank"
                        rel="noreferrer"
                    >
                        "calibrating a classifier"</a
                    >
                    subsection). Authoritative reference for Platt + isotonic in code.
                </li>
                <li>
                    David Rosenberg —
                    <a
                        href="https://davidrosenberg.github.io/ttml2021/calibration/2.calibration.pdf"
                        target="_blank"
                        rel="noreferrer"
                    >
                        Calibration lecture notes (NYU TTML 2021, PDF)</a
                    >. Tight, math-forward treatment of the same ideas.
                </li>
                <li>
                    Google ML Crash Course —
                    <a
                        href="https://developers.google.com/machine-learning/crash-course/classification/prediction-bias"
                        target="_blank"
                        rel="noreferrer"
                    >
                        Prediction bias</a
                    >. The intuition for why average prediction should match
                    average outcome.
                </li>
                <li>
                    Niculescu-Mizil &amp; Caruana (ICML 2005) —
                    <a
                        href="https://www.cs.cornell.edu/~alexn/papers/calibration.icml05.crc.rev3.pdf"
                        target="_blank"
                        rel="noreferrer"
                    >
                        Predicting Good Probabilities With Supervised Learning
                        (PDF)</a
                    >. The empirical paper that put Platt vs. isotonic on the
                    map.
                </li>
            </ul>
        </section>

        <p class="col credits" style="color: var(--ink-soft); font-size: 14px;">
            Made with d3 + Svelte + scikit-learn. Code and notebooks in the
            <a
                href="https://github.com/rexarski/probably-not-probabilities"
                target="_blank"
                rel="noreferrer">repository</a
            >.
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
        content: "";
        width: 1px;
        height: 28px;
        background: linear-gradient(var(--green-soft), transparent);
    }
    @keyframes cue {
        0%,
        100% {
            transform: translateY(0);
            opacity: 0.55;
        }
        50% {
            transform: translateY(6px);
            opacity: 1;
        }
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
    .reasons {
        list-style: none;
        padding: 0;
        margin: 12px 0 18px;
        display: grid;
        gap: 10px;
    }
    .reasons li {
        padding: 10px 14px 10px 16px;
        border-left: 2px solid var(--green-dim);
        background: var(--bg-alt);
        font-size: 15px;
        line-height: 1.55;
        color: var(--ink-soft);
    }
    .reasons li strong {
        color: var(--ink);
        font-weight: 600;
    }
    .axis-key {
        margin: 18px 0 8px;
    }
    .key-table {
        width: 100%;
        border-collapse: collapse;
        font-family: var(--sans);
        font-size: 14px;
        margin: 12px 0 10px;
        border: 1px solid var(--rule);
        border-radius: 6px;
        overflow: hidden;
    }
    .key-table th,
    .key-table td {
        padding: 10px 12px;
        text-align: left;
        border-bottom: 1px solid var(--rule);
    }
    .key-table thead {
        background: var(--bg-alt);
    }
    .key-table th {
        color: var(--ink-soft);
        font-weight: 500;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .key-table th span {
        display: inline-block;
        margin-left: 4px;
        padding: 1px 5px;
        border-radius: 3px;
        background: rgba(29, 185, 84, 0.18);
        color: var(--green-soft);
        font-family: var(--mono);
        font-style: italic;
        text-transform: none;
        letter-spacing: 0;
        font-size: 11px;
    }
    .key-table tbody tr:last-child td {
        border-bottom: 0;
    }
    .key-table .ok {
        color: var(--green-soft);
    }
    .key-table .bad {
        color: var(--orange);
    }
    .key-caption {
        font-size: 13px;
        color: var(--ink-soft);
        margin: 0;
    }
    /* Part 1 figure grid: histogram on left, ROC chart in the sidenote slot. */
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
    .roc-wrap {
        align-self: start;
    }
    .roc-caption {
        font-family: var(--sans);
        font-size: 12px;
        line-height: 1.45;
        color: var(--ink-soft);
        margin: 8px 0 0;
    }
    .stat-row {
        grid-column: 1 / -1;
        display: grid;
        grid-template-columns: repeat(3, minmax(140px, 220px));
        gap: 18px;
        margin: 8px 0 20px;
        font-family: var(--sans);
    }
    .stat-row .stat {
        background: var(--bg-alt);
        border: 1px solid var(--rule);
        border-radius: 6px;
        padding: 12px 16px;
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

    /* ---------- Timeline / table-of-contents nav ---------- */
    .toc {
        position: fixed;
        left: 22px;
        top: 50%;
        transform: translateY(-50%);
        z-index: 30;
        font-family: var(--sans);
        pointer-events: auto;
    }
    .toc ul {
        list-style: none;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    .toc li {
        margin: 0;
    }
    .toc a {
        display: flex;
        align-items: baseline;
        gap: 10px;
        padding: 6px 10px 6px 12px;
        border-left: 1px solid var(--rule);
        color: var(--ink-soft);
        font-size: 11px;
        letter-spacing: 0.02em;
        background: none;
        text-decoration: none;
        transition:
            color 0.2s,
            border-color 0.2s,
            opacity 0.2s;
        opacity: 0.55;
    }
    .toc a:hover {
        color: var(--ink);
        border-left-color: var(--green-dim);
        background: none;
        opacity: 1;
    }
    .toc a .num {
        font-family: var(--mono);
        font-size: 10px;
        color: var(--ink-soft);
        letter-spacing: 0.04em;
    }
    .toc a .lab {
        font-size: 11px;
    }
    .toc li.active a {
        color: var(--ink);
        border-left-color: var(--green);
        opacity: 1;
    }
    .toc li.active a .num {
        color: var(--green-soft);
    }
    @media (max-width: 1280px) {
        .toc {
            display: none;
        }
    }
</style>
