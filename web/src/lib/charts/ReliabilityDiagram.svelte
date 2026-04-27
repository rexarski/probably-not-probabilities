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
   *   activeId?: string | null
   * }} */
  let {
    series = [],
    width = 520,
    height = 380,
    title = 'Reliability diagram',
    subtitle = 'Predicted score vs. observed hit rate, binned',
    activeId = null
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
</script>

<figure class="rd">
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
              stroke-width="1" />
          {/each}
        </g>
      {/each}

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
</figure>

<style>
  .rd {
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
     attribute normalises the dasharray independent of true length. */
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
</style>
