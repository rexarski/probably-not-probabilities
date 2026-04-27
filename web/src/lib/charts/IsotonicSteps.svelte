<script>
  import * as d3 from 'd3';
  import { palette } from '../theme.js';

  /** @type {{
   *   steps: { x: number, y: number }[],
   *   width?: number,
   *   height?: number,
   *   title?: string,
   *   subtitle?: string,
   *   probe?: number,
   *   maxKnots?: number
   * }} */
  let {
    steps = [],
    width = 460,
    height = 320,
    title = 'Isotonic regression: a monotone step function',
    subtitle = 'PAVA fits the best non-decreasing mapping from scores to actual hit rates',
    probe = 0.7,
    maxKnots = 0
  } = $props();

  const margin = { top: 56, right: 18, bottom: 44, left: 50 };
  let innerW = $derived(width - margin.left - margin.right);
  let innerH = $derived(height - margin.top - margin.bottom);
  let x = $derived(d3.scaleLinear().domain([0, 1]).range([0, innerW]));
  let y = $derived(d3.scaleLinear().domain([0, 1]).range([innerH, 0]));

  // Optionally subsample the step function to show how fewer knots produce a
  // coarser staircase — pedagogical for the "isotonic can overfit" point.
  let displayedSteps = $derived.by(() => {
    const sorted = [...steps].sort((a, b) => a.x - b.x);
    if (!maxKnots || maxKnots >= sorted.length) return sorted;
    const stride = sorted.length / maxKnots;
    const picked = [];
    for (let i = 0; i < maxKnots; i++) {
      picked.push(sorted[Math.min(sorted.length - 1, Math.round(i * stride))]);
    }
    if (picked[picked.length - 1] !== sorted[sorted.length - 1]) {
      picked.push(sorted[sorted.length - 1]);
    }
    return picked;
  });

  let path = $derived.by(() => {
    if (!displayedSteps.length) return '';
    const cmds = [`M ${x(displayedSteps[0].x)} ${y(displayedSteps[0].y)}`];
    for (let i = 1; i < displayedSteps.length; i++) {
      cmds.push(`L ${x(displayedSteps[i].x)} ${y(displayedSteps[i - 1].y)}`);
      cmds.push(`L ${x(displayedSteps[i].x)} ${y(displayedSteps[i].y)}`);
    }
    return cmds.join(' ');
  });

  // Evaluate the (possibly subsampled) step function at the probe x.
  let probeY = $derived.by(() => {
    if (!displayedSteps.length) return 0;
    let v = displayedSteps[0].y;
    for (const s of displayedSteps) {
      if (s.x <= probe) v = s.y;
      else break;
    }
    return v;
  });

  const ticks = [0, 0.25, 0.5, 0.75, 1];
</script>

<figure>
  <svg viewBox="0 0 {width} {height}" role="img" aria-label={title}>
    <text class="title" x={margin.left} y="20">{title}</text>
    <text class="subtitle" x={margin.left} y="36">{subtitle}</text>

    <g transform="translate({margin.left}, {margin.top})">
      {#each ticks as t}
        <line
          x1={x(t)}
          x2={x(t)}
          y1="0"
          y2={innerH}
          stroke={palette.rule}
          stroke-dasharray="2 4" />
        <line
          y1={y(t)}
          y2={y(t)}
          x1="0"
          x2={innerW}
          stroke={palette.rule}
          stroke-dasharray="2 4" />
      {/each}
      <line
        x1={x(0)}
        y1={y(0)}
        x2={x(1)}
        y2={y(1)}
        stroke={palette.diagonal}
        stroke-dasharray="6 4" />
      <path d={path} fill="none" stroke={palette.green} stroke-width="2.5" />
      {#each displayedSteps as s}
        <circle cx={x(s.x)} cy={y(s.y)} r="2.5" fill={palette.greenSoft} />
      {/each}

      <!-- Probe cross-hair: vertical line at probe x, horizontal at probeY -->
      <line
        x1={x(probe)}
        x2={x(probe)}
        y1={y(probeY)}
        y2={innerH}
        stroke={palette.ink}
        stroke-opacity="0.5"
        stroke-dasharray="3 3" />
      <line
        x1="0"
        x2={x(probe)}
        y1={y(probeY)}
        y2={y(probeY)}
        stroke={palette.ink}
        stroke-opacity="0.5"
        stroke-dasharray="3 3" />
      <circle
        cx={x(probe)}
        cy={y(probeY)}
        r="5"
        fill={palette.green}
        stroke={palette.bg}
        stroke-width="2" />
      <text
        class="probe-tag"
        x={x(probe) + 8}
        y={y(probeY) - 8}>
        {probe.toFixed(2)} → {probeY.toFixed(3)}
      </text>

      {#each ticks as t}
        <text class="axtick" x={x(t)} y={innerH + 16} text-anchor="middle">
          {t.toFixed(2)}
        </text>
        <text class="axtick" x={-8} y={y(t) + 4} text-anchor="end">
          {t.toFixed(2)}
        </text>
      {/each}
      <text class="axlabel" x={innerW / 2} y={innerH + 34} text-anchor="middle">
        Raw score
      </text>
      <text
        class="axlabel"
        x={-innerH / 2}
        y={-36}
        text-anchor="middle"
        transform="rotate(-90)">
        Calibrated probability
      </text>
    </g>
  </svg>
</figure>

<style>
  figure {
    margin: 0;
    width: 100%;
  }
  svg {
    width: 100%;
    height: auto;
    display: block;
  }
  .title {
    fill: var(--ink, #e8e8e3);
    font-family: var(--serif);
    font-size: 15px;
    font-weight: 600;
  }
  .subtitle {
    fill: var(--ink-soft, #a7a7a2);
    font-family: var(--sans);
    font-size: 11px;
  }
  .axtick {
    fill: var(--ink-soft, #a7a7a2);
    font-family: var(--mono);
    font-size: 10px;
  }
  .axlabel {
    fill: var(--ink, #e8e8e3);
    font-family: var(--sans);
    font-size: 11px;
  }
  .probe-tag {
    fill: var(--ink, #e8e8e3);
    font-family: var(--mono);
    font-size: 11px;
  }
</style>
