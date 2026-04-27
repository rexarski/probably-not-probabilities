<script>
  import * as d3 from 'd3';
  import { palette } from '../theme.js';

  /** @type {{
   *   a: number,
   *   b: number,
   *   width?: number,
   *   height?: number,
   *   title?: string,
   *   subtitle?: string
   * }} */
  let {
    a = 1.0,
    b = 0.0,
    width = 460,
    height = 320,
    title = 'Platt scaling: σ(a · s + b)',
    subtitle = 'A learned sigmoid that re-maps raw scores into calibrated probabilities'
  } = $props();

  const margin = { top: 56, right: 18, bottom: 44, left: 50 };
  let innerW = $derived(width - margin.left - margin.right);
  let innerH = $derived(height - margin.top - margin.bottom);
  let x = $derived(d3.scaleLinear().domain([0, 1]).range([0, innerW]));
  let y = $derived(d3.scaleLinear().domain([0, 1]).range([innerH, 0]));

  function sigmoid(s) {
    return 1 / (1 + Math.exp(-(a * s + b)));
  }

  let curve = $derived.by(() => {
    const pts = [];
    for (let i = 0; i <= 100; i++) {
      const s = i / 100;
      pts.push([x(s), y(sigmoid(s))]);
    }
    return d3.line()(pts);
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
      <path d={curve} fill="none" stroke={palette.green} stroke-width="2.5" />

      {#each ticks as t}
        <text class="axtick" x={x(t)} y={innerH + 16} text-anchor="middle">
          {t.toFixed(2)}
        </text>
        <text class="axtick" x={-8} y={y(t) + 4} text-anchor="end">
          {t.toFixed(2)}
        </text>
      {/each}
      <text class="axlabel" x={innerW / 2} y={innerH + 34} text-anchor="middle">
        Raw score s
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
</style>
