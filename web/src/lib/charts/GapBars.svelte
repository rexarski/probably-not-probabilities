<script>
  import * as d3 from 'd3';
  import { palette } from '../theme.js';

  /** @type {{
   *   points: { bin_lo: number, bin_hi: number, mean_pred: number, frac_pos: number, count: number }[],
   *   color?: string,
   *   width?: number,
   *   height?: number,
   *   title?: string,
   *   subtitle?: string
   * }} */
  let {
    points = [],
    color = palette.overConfident,
    width = 540,
    height = 280,
    title = 'Predicted vs. actual hit rate, per score bin',
    subtitle = 'Bars show mean predicted score; rules show actual rate. The gap is calibration error.'
  } = $props();

  const margin = { top: 60, right: 18, bottom: 44, left: 50 };
  let innerW = $derived(width - margin.left - margin.right);
  let innerH = $derived(height - margin.top - margin.bottom);

  let x = $derived(
    d3
      .scaleBand()
      .domain(points.map((_, i) => i))
      .range([0, innerW])
      .padding(0.18)
  );
  let y = $derived(d3.scaleLinear().domain([0, 1]).range([innerH, 0]));
  const yTicks = [0, 0.25, 0.5, 0.75, 1];

  let figEl = $state(null);
  let tt = $state(null);

  function showTip(event, p) {
    if (!figEl) return;
    const rect = figEl.getBoundingClientRect();
    tt = {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
      flip: event.clientX - rect.left > rect.width * 0.6,
      bin: `${p.bin_lo.toFixed(2)}–${p.bin_hi.toFixed(2)}`,
      pred: p.mean_pred.toFixed(3),
      actual: p.frac_pos.toFixed(3),
      gap: Math.abs(p.mean_pred - p.frac_pos).toFixed(3),
      count: p.count
    };
  }
  function hideTip() { tt = null; }
</script>

<figure bind:this={figEl}>
  <svg viewBox="0 0 {width} {height}" role="img" aria-label={title}>
    <text class="title" x={margin.left} y="20">{title}</text>
    <text class="subtitle" x={margin.left} y="38">{subtitle}</text>

    <g transform="translate({margin.left}, {margin.top})">
      {#each yTicks as t}
        <line
          x1="0"
          x2={innerW}
          y1={y(t)}
          y2={y(t)}
          stroke={palette.rule}
          stroke-dasharray="2 4" />
        <text class="axtick" x={-8} y={y(t) + 4} text-anchor="end">
          {t.toFixed(2)}
        </text>
      {/each}

      {#each points as p, i}
        {@const xb = x(i)}
        {@const w = x.bandwidth()}
        <rect
          x={xb}
          y={y(p.mean_pred)}
          width={w}
          height={innerH - y(p.mean_pred)}
          fill={color}
          fill-opacity="0.55" />
        <line
          x1={xb - 2}
          x2={xb + w + 2}
          y1={y(p.frac_pos)}
          y2={y(p.frac_pos)}
          stroke={palette.ink}
          stroke-width="2" />
        <!-- gap shading -->
        <rect
          x={xb + w * 0.35}
          y={Math.min(y(p.mean_pred), y(p.frac_pos))}
          width={w * 0.3}
          height={Math.abs(y(p.mean_pred) - y(p.frac_pos))}
          fill={palette.ink}
          fill-opacity="0.12" />
        <!-- pointer hit target spans the full bar column -->
        <rect
          class="hit"
          x={xb}
          y="0"
          width={w}
          height={innerH}
          fill="transparent"
          onpointerenter={(e) => showTip(e, p)}
          onpointermove={(e) => showTip(e, p)}
          onpointerleave={hideTip} />
      {/each}

      <line x1="0" x2={innerW} y1={innerH} y2={innerH} stroke={palette.rule} />
      {#each points as p, i}
        {#if i % 2 === 0}
          <text
            class="axtick"
            x={x(i) + x.bandwidth() / 2}
            y={innerH + 14}
            text-anchor="middle">
            {((p.bin_lo + p.bin_hi) / 2).toFixed(2)}
          </text>
        {/if}
      {/each}
      <text class="axlabel" x={innerW / 2} y={innerH + 34} text-anchor="middle">
        Score bin (center)
      </text>
    </g>
  </svg>

  {#if tt}
    <div
      class="tt"
      class:flip={tt.flip}
      style:left="{tt.x}px"
      style:top="{tt.y}px">
      <div class="tt-row"><span>Bin</span><span>{tt.bin}</span></div>
      <div class="tt-row"><span>Predicted</span><span>{tt.pred}</span></div>
      <div class="tt-row"><span>Actual</span><span>{tt.actual}</span></div>
      <div class="tt-row"><span>Gap</span><span>{tt.gap}</span></div>
      <div class="tt-row"><span>n</span><span>{tt.count}</span></div>
    </div>
  {/if}
</figure>

<style>
  figure {
    margin: 0;
    width: 100%;
    position: relative;
  }
  .hit {
    cursor: crosshair;
  }
  .tt {
    position: absolute;
    pointer-events: none;
    transform: translate(14px, -50%);
    background: var(--bg-alt, #161616);
    border: 1px solid var(--rule, #2a2a2a);
    padding: 8px 10px;
    min-width: 152px;
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
</style>
