<script>
  import * as d3 from 'd3';
  import { palette } from '../theme.js';

  /** @type {{
   *   series: { id: string, label: string, color: string, points: {fpr:number,tpr:number}[], auc: number }[],
   *   activeId?: string | null,
   *   width?: number,
   *   height?: number,
   *   title?: string,
   *   subtitle?: string
   * }} */
  let {
    series = [],
    activeId = null,
    width = 320,
    height = 320,
    title = 'ROC curve',
    subtitle = 'Ranking quality — same for all three'
  } = $props();

  const margin = { top: 50, right: 14, bottom: 44, left: 44 };
  let innerW = $derived(width - margin.left - margin.right);
  let innerH = $derived(height - margin.top - margin.bottom);
  let x = $derived(d3.scaleLinear().domain([0, 1]).range([0, innerW]));
  let y = $derived(d3.scaleLinear().domain([0, 1]).range([innerH, 0]));

  function path(points) {
    return d3
      .line()
      .x((d) => x(d.fpr))
      .y((d) => y(d.tpr))(points);
  }

  const ticks = [0, 0.5, 1];
</script>

<figure class="roc">
  <svg viewBox="0 0 {width} {height}" role="img" aria-label={title}>
    <text class="title" x={margin.left} y="20">{title}</text>
    <text class="subtitle" x={margin.left} y="36">{subtitle}</text>

    <g transform="translate({margin.left}, {margin.top})">
      <!-- chance diagonal -->
      <line
        x1={x(0)} y1={y(0)} x2={x(1)} y2={y(1)}
        stroke={palette.rule} stroke-dasharray="3 4" />

      <!-- inactive series first -->
      {#each series as s (s.id)}
        {@const dim = activeId && s.id !== activeId}
        <path
          d={path(s.points)}
          fill="none"
          stroke={dim ? palette.rule : s.color}
          stroke-opacity={dim ? 0.5 : activeId ? 1 : 0.85}
          stroke-width={dim ? 1 : activeId ? 2.4 : 1.4} />
      {/each}

      <!-- axes -->
      <line x1={0} x2={innerW} y1={innerH} y2={innerH} stroke={palette.rule} />
      <line x1={0} x2={0} y1={0} y2={innerH} stroke={palette.rule} />
      {#each ticks as t}
        <text class="axtick" x={x(t)} y={innerH + 14} text-anchor="middle">
          {t}
        </text>
        <text class="axtick" x={-6} y={y(t) + 3} text-anchor="end">{t}</text>
      {/each}
      <text class="axlabel" x={innerW / 2} y={innerH + 32} text-anchor="middle">
        False positive rate
      </text>
      <text
        class="axlabel"
        x={-innerH / 2}
        y={-32}
        text-anchor="middle"
        transform="rotate(-90)">
        True positive rate
      </text>

      <!-- AUC annotation -->
      {#if activeId}
        {#each series as s (s.id)}
          {#if s.id === activeId}
            <text
              class="auc"
              x={innerW - 6}
              y={innerH - 8}
              text-anchor="end"
              fill={s.color}>
              AUC = {s.auc.toFixed(3)}
            </text>
          {/if}
        {/each}
      {:else}
        <text
          class="auc"
          x={innerW - 6}
          y={innerH - 8}
          text-anchor="end"
          fill={palette.inkSoft}>
          AUC ≈ {(series[0]?.auc ?? 0).toFixed(3)} (all three)
        </text>
      {/if}
    </g>
  </svg>
</figure>

<style>
  .roc {
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
    font-size: 14px;
    font-weight: 600;
  }
  .subtitle {
    fill: var(--ink-soft, #a7a7a2);
    font-family: var(--sans);
    font-size: 10.5px;
  }
  .axtick {
    fill: var(--ink-soft, #a7a7a2);
    font-family: var(--mono);
    font-size: 10px;
  }
  .axlabel {
    fill: var(--ink, #e8e8e3);
    font-family: var(--sans);
    font-size: 10.5px;
  }
  .auc {
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 600;
  }
</style>
