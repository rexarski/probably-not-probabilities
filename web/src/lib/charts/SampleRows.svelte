<script>
  import { palette } from '../theme.js';

  /** @type {{
   *   rows: {
   *     track: string,
   *     artist: string,
   *     popularity: number,
   *     is_hit: number,
   *     p_over: number,
   *     p_under: number,
   *     p_base: number
   *   }[],
   *   visibleCount?: number
   * }} */
  let { rows = [], visibleCount = 0 } = $props();

  function decision(p, t = 0.5) {
    return p >= t ? 'hit' : 'miss';
  }
  function correct(p, truth) {
    return decision(p) === (truth === 1 ? 'hit' : 'miss');
  }
</script>

<div class="rows">
  <div class="header">
    <span class="col-track">Track</span>
    <span class="col-truth">Actual</span>
    <span class="col-score over">Over‑confident score</span>
    <span class="col-score under">Under‑confident score</span>
  </div>

  {#each rows.slice(0, visibleCount) as r, i (r.track + i)}
    <div class="row" style:animation-delay="{i * 60}ms">
      <span class="col-track">
        <span class="track-name">{r.track}</span>
        <span class="artist">{r.artist}</span>
      </span>
      <span class="col-truth">
        <span class="badge" class:hit={r.is_hit === 1}>
          {r.is_hit === 1 ? 'hit' : 'miss'}
        </span>
        <span class="pop">pop {r.popularity}</span>
      </span>
      <span class="col-score">
        <span class="bar-cell">
          <span
            class="bar"
            style:width="{r.p_over * 100}%"
            style:background={palette.overConfident}></span>
          <span class="bar-val">{r.p_over.toFixed(2)}</span>
        </span>
        <span class="dec" class:right={correct(r.p_over, r.is_hit)}>
          {correct(r.p_over, r.is_hit) ? '✓ correct' : '✗ wrong'}
        </span>
      </span>
      <span class="col-score">
        <span class="bar-cell">
          <span
            class="bar"
            style:width="{r.p_under * 100}%"
            style:background={palette.underConfident}></span>
          <span class="bar-val">{r.p_under.toFixed(2)}</span>
        </span>
        <span class="dec" class:right={correct(r.p_under, r.is_hit)}>
          {correct(r.p_under, r.is_hit) ? '✓ correct' : '✗ wrong'}
        </span>
      </span>
    </div>
  {/each}
</div>

<style>
  .rows {
    display: grid;
    gap: 6px;
    font-family: var(--sans);
    font-size: 13px;
    color: var(--ink);
  }
  .header,
  .row {
    display: grid;
    grid-template-columns: 1.6fr 0.7fr 1.5fr 1.5fr;
    gap: 14px;
    align-items: center;
    padding: 10px 12px;
    border-radius: 6px;
  }
  .header {
    color: var(--ink-soft);
    font-size: 11px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    border-bottom: 1px solid var(--rule);
    padding-bottom: 8px;
    background: transparent;
  }
  .header .over {
    color: #ff7a59;
  }
  .header .under {
    color: #7ab7ff;
  }
  .row {
    background: var(--surface);
    opacity: 0;
    transform: translateY(8px);
    animation: fadeIn 0.5s forwards;
  }
  @keyframes fadeIn {
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  .col-track {
    display: flex;
    flex-direction: column;
  }
  .track-name {
    font-weight: 600;
  }
  .artist {
    color: var(--ink-soft);
    font-size: 11px;
  }
  .col-truth {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .badge {
    font-family: var(--mono);
    font-size: 10px;
    padding: 2px 6px;
    border: 1px solid var(--rule);
    border-radius: 99px;
    color: var(--ink-soft);
  }
  .badge.hit {
    color: var(--bg);
    background: var(--green);
    border-color: var(--green);
  }
  .pop {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--ink-soft);
  }
  .col-score {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .bar-cell {
    position: relative;
    background: var(--bg-alt);
    border-radius: 3px;
    height: 18px;
    overflow: hidden;
  }
  .bar {
    position: absolute;
    inset: 0 auto 0 0;
    opacity: 0.85;
  }
  .bar-val {
    position: absolute;
    right: 6px;
    top: 50%;
    transform: translateY(-50%);
    font-family: var(--mono);
    font-size: 11px;
    color: var(--ink);
    text-shadow: 0 0 3px rgba(0, 0, 0, 0.7);
  }
  .dec {
    font-family: var(--mono);
    font-size: 10px;
    color: #ff7a59;
  }
  .dec.right {
    color: var(--green);
  }
</style>
