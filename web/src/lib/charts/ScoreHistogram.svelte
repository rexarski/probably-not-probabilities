<script>
  import * as d3 from 'd3';
  import { palette } from '../theme.js';

  /** @type {{
   *   bins: { x0: number, x1: number, count: number }[],
   *   width?: number,
   *   height?: number,
   *   threshold?: number,
   *   color?: string,
   *   title?: string,
   *   subtitle?: string,
   *   onThreshold?: (t: number) => void
   * }} */
  let {
    bins = [],
    width = 540,
    height = 280,
    threshold = 0.5,
    color = palette.green,
    title = 'Distribution of predicted scores',
    subtitle = 'Holdout set, score buckets',
    onThreshold = null
  } = $props();

  const margin = { top: 50, right: 18, bottom: 44, left: 50 };
  let innerW = $derived(width - margin.left - margin.right);
  let innerH = $derived(height - margin.top - margin.bottom);
  let x = $derived(d3.scaleLinear().domain([0, 1]).range([0, innerW]));
  let maxCount = $derived(Math.max(1, ...bins.map((b) => b.count)));
  let y = $derived(d3.scaleLinear().domain([0, maxCount]).nice().range([innerH, 0]));

  let svgEl = $state(null);
  let figEl = $state(null);
  let tt = $state(null);

  function showTip(event, b) {
    if (!figEl) return;
    const rect = figEl.getBoundingClientRect();
    tt = {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
      flip: event.clientX - rect.left > rect.width * 0.6,
      bin: `${b.x0.toFixed(2)}–${b.x1.toFixed(2)}`,
      count: b.count
    };
  }
  function hideTip() { tt = null; }

  function handlePointer(event) {
    if (!onThreshold || !svgEl) return;
    const rect = svgEl.getBoundingClientRect();
    const px = ((event.clientX - rect.left) / rect.width) * width - margin.left;
    const t = Math.max(0, Math.min(1, x.invert(px)));
    onThreshold(Math.round(t * 100) / 100);
  }
  const xTicks = [0, 0.25, 0.5, 0.75, 1];
</script>

<figure class="hist" bind:this={figEl}>
  <svg
    bind:this={svgEl}
    viewBox="0 0 {width} {height}"
    role="img"
    aria-label={title}
    onpointerdown={onThreshold ? handlePointer : null}
    onpointermove={(e) => onThreshold && e.buttons === 1 && handlePointer(e)}
    style:cursor={onThreshold ? 'ew-resize' : 'default'}>
    <text class="title" x={margin.left} y="20">{title}</text>
    <text class="subtitle" x={margin.left} y="36">{subtitle}</text>

    <g transform="translate({margin.left}, {margin.top})">
      <!-- bars -->
      {#each bins as b}
        {@const isAbove = (b.x0 + b.x1) / 2 >= threshold}
        <rect
          class="bar"
          x={x(b.x0) + 1}
          y={y(b.count)}
          width={Math.max(0, x(b.x1) - x(b.x0) - 2)}
          height={innerH - y(b.count)}
          fill={color}
          fill-opacity={isAbove ? 0.85 : 0.32}
          onpointerenter={(e) => showTip(e, b)}
          onpointermove={(e) => showTip(e, b)}
          onpointerleave={hideTip} />
      {/each}

      <!-- threshold rule -->
      <line
        x1={x(threshold)}
        x2={x(threshold)}
        y1={-4}
        y2={innerH}
        stroke={palette.ink}
        stroke-width="1.4" />
      <rect
        x={x(threshold) - 32}
        y={-22}
        width="64"
        height="18"
        fill={palette.bgAlt}
        stroke={palette.ink}
        stroke-width="1" />
      <text class="thresh" x={x(threshold)} y={-9} text-anchor="middle">
        t = {threshold.toFixed(2)}
      </text>

      <!-- x axis -->
      <line x1="0" x2={innerW} y1={innerH} y2={innerH} stroke={palette.rule} />
      {#each xTicks as t}
        <text class="axtick" x={x(t)} y={innerH + 16} text-anchor="middle">
          {t.toFixed(2)}
        </text>
      {/each}
      <text class="axlabel" x={innerW / 2} y={innerH + 34} text-anchor="middle">
        Predicted score
      </text>
      <text
        class="axlabel"
        x={-innerH / 2}
        y={-36}
        text-anchor="middle"
        transform="rotate(-90)">
        Count
      </text>
    </g>
  </svg>

  {#if tt}
    <div
      class="tt"
      class:flip={tt.flip}
      style:left="{tt.x}px"
      style:top="{tt.y}px">
      <div class="tt-row"><span>Score</span><span>{tt.bin}</span></div>
      <div class="tt-row"><span>Count</span><span>{tt.count}</span></div>
    </div>
  {/if}
</figure>

<style>
  .hist {
    margin: 0;
    width: 100%;
    position: relative;
  }
  .bar {
    transition: fill-opacity 0.2s;
  }
  .bar:hover {
    fill-opacity: 1 !important;
  }
  .tt {
    position: absolute;
    pointer-events: none;
    transform: translate(14px, -50%);
    background: var(--bg-alt, #161616);
    border: 1px solid var(--rule, #2a2a2a);
    padding: 8px 10px;
    min-width: 132px;
    border-radius: 3px;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.5);
    z-index: 6;
    font-family: var(--mono);
    font-size: 11px;
    line-height: 1.5;
    color: var(--ink, #e8e8e3);
  }
  .tt.flip {
    transform: translate(calc(-100% - 14px), -50%);
  }
  .tt-row {
    display: flex;
    justify-content: space-between;
    gap: 18px;
    color: var(--ink-soft, #a7a7a2);
  }
  .tt-row span:last-child {
    color: var(--ink, #e8e8e3);
  }
  svg {
    width: 100%;
    height: auto;
    display: block;
    user-select: none;
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
  .thresh {
    fill: var(--ink, #e8e8e3);
    font-family: var(--mono);
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
    letter-spacing: 0.04em;
  }
</style>
