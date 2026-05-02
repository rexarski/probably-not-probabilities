<script>
  /** @type {{
   *   active: number,
   *   labels: string[]
   * }} */
  let { active, labels } = $props();
</script>

<ol class="step-dots" aria-label="Scrolly progress">
  {#each labels as lab, i}
    {@const n = i + 1}
    {@const state = active === n ? 'on' : active > n ? 'past' : 'future'}
    <li class="dot-li {state}">
      <span class="num">{n}</span>
      <span class="lab">{lab}</span>
    </li>
  {/each}
</ol>

<style>
  .step-dots {
    list-style: none;
    margin: 0 0 14px;
    padding: 0;
    display: flex;
    gap: 10px;
    align-items: center;
    font-family: var(--mono);
    font-size: 11px;
    flex-wrap: wrap;
  }
  .dot-li {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px 4px 6px;
    border: 1px solid var(--rule, #2a2a2a);
    border-radius: 999px;
    color: var(--ink-soft, #a7a7a2);
    transition: color 0.3s, border-color 0.3s, background 0.3s;
  }
  .dot-li .num {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    display: inline-grid;
    place-items: center;
    background: var(--rule, #2a2a2a);
    color: var(--ink-soft, #a7a7a2);
    font-size: 10px;
    transition: background 0.3s, color 0.3s;
  }
  .dot-li.on {
    color: var(--ink, #e8e8e3);
    border-color: var(--green, #1db954);
    background: rgba(29, 185, 84, 0.08);
  }
  .dot-li.on .num {
    background: var(--green, #1db954);
    color: var(--bg, #0d0d0d);
  }
  .dot-li.past {
    color: var(--ink-soft, #a7a7a2);
    border-color: var(--green-dim, #147a37);
  }
  .dot-li.past .num {
    background: var(--green-dim, #147a37);
    color: var(--ink, #e8e8e3);
  }
  .dot-li .lab {
    letter-spacing: 0.04em;
  }
  @media (max-width: 980px) {
    .step-dots {
      font-size: 10px;
      gap: 6px;
    }
    .dot-li .lab {
      display: none;
    }
  }
</style>
