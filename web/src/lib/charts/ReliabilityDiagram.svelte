<script>
  import * as d3 from 'd3';
  import { palette, fonts } from '../theme.js';

  /**
   * @typedef {{ bin_lo: number, bin_hi: number, mean_pred: number, frac_pos: number, count: number }} Bin
   */

  /** @type {{
   *   series: { id: string, label: string, color?: string, points: Bin[] }[],
   *   width?: number,
   *   height?: number,
   *   title?: string,
   *   subtitle?: string,
   *   activeId?: string | null,
   *   annotations?: Record<string, number> | null
   * }} */
  let {
    series = [],
    width = 520,
    height = 380,
    title = 'Reliability diagram',
    subtitle = 'Predicted score vs. observed hit rate, binned',
    activeId = null,
    annotations = null
  } = $props();

  const margin = { top: 62, right: 24, bottom: 60, left: 64 };

  let innerW = $derived(width - margin.left - margin.right);
  let innerH = $derived(height - margin.top - margin.bottom);

  let x = $derived(d3.scaleLinear().domain([0, 1]).range([0, innerW]));
  let y = $derived(d3.scaleLinear().domain([0, 1]).range([innerH, 0]));

  const ticks = [0, 0.2, 0.4, 0.6, 0.8, 1];

  function path(points) {
    const line = d3
      .line()
      .x((d) => x(d.mean_pred))
      .y((d) => y(d.frac_pos))
      .curve(d3.curveMonotoneX);
    return line(points);
  }

  function radius(count, maxCount) {
    return 3 + 5 * Math.sqrt(count / Math.max(maxCount, 1));
  }

  let maxCount = $derived(
    Math.max(1, ...series.flatMap((s) => s.points.map((p) => p.count)))
  );

  let figEl = $state(null);
  let tt = $state(null);

  function showTip(event, label, color, p) {
    if (!figEl) return;
    const rect = figEl.getBoundingClientRect();
    tt = {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
      flip: event.clientX - rect.left > rect.width * 0.6,
      label,
      color,
      bin: `${p.bin_lo.toFixed(2)}–${p.bin_hi.toFixed(2)}`,
      pred: p.mean_pred.toFixed(3),
      actual: p.frac_pos.toFixed(3),
      gap: Math.abs(p.mean_pred - p.frac_pos).toFixed(3),
      count: p.count
    };
  }
  function hideTip() { tt = null; }
</script>

<figure class="rd" bind:this={figEl}>
  <svg viewBox="0 0 {width} {height}" role="img" aria-label={title}>
    <text class="title" x={margin.left} y="24">{title}</text>
    <text class="subtitle" x={margin.left} y="44">{subtitle}</text>

    <g transform="translate({margin.left}, {margin.top})">
      <!-- Grid -->
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

      <!-- Diagonal: perfect calibration -->
      <line
        x1={x(0)}
        y1={y(0)}
        x2={x(1)}
        y2={y(1)}
        stroke={palette.diagonal}
        stroke-width="1.4"
        stroke-dasharray="6 4" />

      <!-- Series. Re-key on activeId so the active path replays its draw-in. -->
      {#each series as s (s.id)}
        {@const isActive = activeId == null || activeId === s.id}
        {@const isFocus = activeId === s.id}
        {@const color = s.color ?? palette.green}
        <g class:dim={!isActive} class:focus={isFocus}>
          {#key isFocus ? `${s.id}-on` : `${s.id}-off`}
            <path
              class="series-path"
              class:draw={isFocus}
              d={path(s.points)}
              fill="none"
              stroke={color}
              stroke-width={isActive ? 2.5 : 1.5}
              stroke-linejoin="round"
              stroke-linecap="round"
              pathLength={isFocus ? 1 : undefined} />
          {/key}
          {#each s.points as p}
            <circle
              class="series-pt"
              cx={x(p.mean_pred)}
              cy={y(p.frac_pos)}
              r={radius(p.count, maxCount) * (isFocus ? 1.25 : 1)}
              fill={color}
              fill-opacity={isActive ? 0.85 : 0.4}
              stroke={palette.bg}
              stroke-width="1"
              onpointerenter={(e) => showTip(e, s.label, color, p)}
              onpointermove={(e) => showTip(e, s.label, color, p)}
              onpointerleave={hideTip} />
          {/each}
        </g>
      {/each}

      <!-- ECE annotations: deferred until reader scrolls into the ECE
           introduction step. Sits in the upper-left of the plot so it
           never collides with the curves. -->
      {#if annotations}
        <g class="ece-anno" transform="translate(12, 10)">
          <text class="ece-anno-h" x="0" y="0">Expected Calibration Error</text>
          {#each series as s, i (s.id)}
            {@const v = annotations[s.id]}
            {#if v != null}
              <g transform="translate(0, {18 + i * 18})">
                <circle cx="5" cy="-4" r="4" fill={s.color ?? palette.green} />
                <text class="ece-anno-l" x="14" y="0">{s.label}</text>
                <text class="ece-anno-v" x="180" y="0" text-anchor="end" fill={s.color ?? palette.green}>
                  {v.toFixed(3)}
                </text>
              </g>
            {/if}
          {/each}
        </g>
      {/if}

      <!-- Axes -->
      <g class="axis">
        {#each ticks as t}
          <text x={x(t)} y={innerH + 22} text-anchor="middle">{t.toFixed(1)}</text>
        {/each}
        {#each ticks as t}
          <text x={-10} y={y(t) + 5} text-anchor="end">{t.toFixed(1)}</text>
        {/each}
        <text class="axis-label" x={innerW / 2} y={innerH + 46} text-anchor="middle">
          Predicted score
        </text>
        <text
          class="axis-label"
          x={-innerH / 2}
          y={-46}
          text-anchor="middle"
          transform="rotate(-90)">
          Fraction of hits
        </text>
      </g>
    </g>
  </svg>

  {#if series.length > 1}
    <ul class="legend">
      {#each series as s (s.id)}
        <li class:dim={activeId != null && activeId !== s.id}>
          <span class="swatch" style:background={s.color ?? palette.green}></span>
          {s.label}
        </li>
      {/each}
      <li class="legend-perfect">
        <span class="dash"></span> perfect
      </li>
    </ul>
  {/if}

  {#if tt}
    <div
      class="tt"
      class:flip={tt.flip}
      style:left="{tt.x}px"
      style:top="{tt.y}px">
      <div class="tt-h"><span class="dot" style:background={tt.color}></span>{tt.label}</div>
      <div class="tt-row"><span>Bin</span><span>{tt.bin}</span></div>
      <div class="tt-row"><span>Predicted</span><span>{tt.pred}</span></div>
      <div class="tt-row"><span>Actual</span><span>{tt.actual}</span></div>
      <div class="tt-row"><span>Gap</span><span>{tt.gap}</span></div>
      <div class="tt-row"><span>n</span><span>{tt.count}</span></div>
    </div>
  {/if}
</figure>

<style>
  .rd {
    margin: 0;
    width: 100%;
    position: relative;
  }
  .series-pt {
    cursor: crosshair;
  }
  .tt {
    position: absolute;
    pointer-events: none;
    transform: translate(14px, -50%);
    background: var(--bg-alt, #161616);
    border: 1px solid var(--rule, #2a2a2a);
    padding: 8px 10px;
    min-width: 168px;
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
  .tt-h {
    font-family: var(--sans);
    font-size: 12px;
    font-weight: 600;
    color: var(--ink, #e8e8e3);
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 4px;
  }
  .tt-h .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
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
    font-size: 19px;
    font-weight: 600;
  }
  .subtitle {
    fill: var(--ink-soft, #a7a7a2);
    font-family: var(--sans);
    font-size: 13px;
  }
  .axis text {
    fill: var(--ink-soft, #a7a7a2);
    font-family: var(--mono);
    font-size: 13px;
  }
  .axis-label {
    fill: var(--ink, #e8e8e3) !important;
    font-family: var(--sans) !important;
    font-size: 14px !important;
    letter-spacing: 0.04em;
  }
  .dim {
    opacity: 0.35;
    transition: opacity 0.4s;
  }
  .series-pt {
    transition: r 0.45s cubic-bezier(0.4, 0, 0.2, 1),
      fill-opacity 0.4s;
  }
  /* Draw-on animation for the focused series so cycling between methods
     feels like the line is being redrawn. The path's pathLength="1"
     attribute normalizes the dasharray independent of true length. */
  .series-path.draw {
    stroke-dasharray: 1;
    stroke-dashoffset: 1;
    animation: draw 0.7s ease-out forwards;
  }
  @keyframes draw {
    to {
      stroke-dashoffset: 0;
    }
  }
  .legend {
    list-style: none;
    padding: 0;
    margin: 10px 16px 0;
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    font-family: var(--sans);
    font-size: 14px;
    color: var(--ink-soft, #a7a7a2);
  }
  .legend li {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: opacity 0.4s;
  }
  .legend li.dim {
    opacity: 0.45;
  }
  .swatch {
    width: 12px;
    height: 12px;
    border-radius: 2px;
    display: inline-block;
  }
  .dash {
    width: 14px;
    border-top: 1.5px dashed var(--ink-soft, #a7a7a2);
    display: inline-block;
  }
  .ece-anno {
    animation: anno-fade 0.6s ease-out both;
  }
  .ece-anno-h {
    fill: var(--ink-soft, #a7a7a2);
    font-family: var(--sans);
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .ece-anno-l {
    fill: var(--ink, #e8e8e3);
    font-family: var(--sans);
    font-size: 13px;
  }
  .ece-anno-v {
    font-family: var(--mono);
    font-size: 13px;
    font-weight: 600;
  }
  @keyframes anno-fade {
    from { opacity: 0; transform: translateY(-4px); }
    to   { opacity: 1; transform: translateY(0); }
  }
</style>
