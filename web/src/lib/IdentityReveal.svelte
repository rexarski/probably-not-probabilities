<script>
  import { onMount } from 'svelte';
  import { palette } from './theme.js';

  let revealed = $state(false);
  let el = $state(null);

  const items = [
    { letter: 'A', label: 'well-calibrated', color: palette.wellCalibrated },
    { letter: 'B', label: 'over-confident',  color: palette.overConfident },
    { letter: 'C', label: 'under-confident', color: palette.underConfident }
  ];

  onMount(() => {
    if (typeof window === 'undefined') return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      revealed = true;
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            revealed = true;
            io.disconnect();
            break;
          }
        }
      },
      { threshold: 0.5 }
    );
    io.observe(el);
    return () => io.disconnect();
  });
</script>

<div class="reveal-row" class:on={revealed} bind:this={el}>
  {#each items as it, i}
    <div
      class="pill"
      style:--c={it.color}
      style:--delay="{i * 160}ms">
      <span class="letter">{it.letter}</span>
      <span class="label">{it.label}</span>
    </div>
  {/each}
</div>

<style>
  .reveal-row {
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
    margin: 8px 0 28px;
  }
  .pill {
    display: inline-flex;
    align-items: center;
    padding: 10px 16px;
    border: 1.5px solid var(--c);
    border-radius: 999px;
    background: color-mix(in srgb, var(--c) 8%, transparent);
    transition:
      box-shadow 0.6s var(--delay) ease,
      transform 0.6s var(--delay) cubic-bezier(0.2, 0.7, 0.2, 1);
    transform: translateY(2px);
  }
  .reveal-row.on .pill {
    transform: translateY(0);
    box-shadow: 0 0 0 4px color-mix(in srgb, var(--c) 14%, transparent);
  }
  .letter {
    font-family: var(--serif);
    font-size: 22px;
    font-weight: 600;
    color: var(--c);
    line-height: 1;
  }
  .label {
    font-family: var(--sans);
    font-size: 14px;
    letter-spacing: 0.02em;
    color: var(--ink, #e8e8e3);
    max-width: 0;
    overflow: hidden;
    white-space: nowrap;
    opacity: 0;
    margin-left: 0;
    transition:
      max-width 0.6s var(--delay) cubic-bezier(0.2, 0.7, 0.2, 1),
      opacity 0.45s calc(var(--delay) + 120ms) ease,
      margin-left 0.6s var(--delay) ease;
  }
  .reveal-row.on .label {
    max-width: 200px;
    opacity: 1;
    margin-left: 12px;
  }
  .reveal-row.on .label::before {
    content: '·';
    color: var(--ink-soft, #a7a7a2);
    margin-right: 8px;
  }
  @media (max-width: 640px) {
    .reveal-row {
      flex-direction: column;
      gap: 10px;
    }
    .pill { width: max-content; }
  }
</style>
