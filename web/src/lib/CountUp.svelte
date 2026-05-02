<script>
  import { onMount } from 'svelte';

  /** @type {{
   *   value: number,
   *   format?: (v: number) => string,
   *   duration?: number,
   *   threshold?: number
   * }} */
  let {
    value,
    format = (v) => Math.round(v).toString(),
    duration = 700,
    threshold = 0.4
  } = $props();

  let display = $state(0);
  let played = $state(false);
  let el = $state(null);

  $effect(() => {
    if (played) display = value;
  });

  onMount(() => {
    if (typeof window === 'undefined') return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      played = true;
      display = value;
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting && !played) {
            run(value);
            io.disconnect();
            break;
          }
        }
      },
      { threshold }
    );
    io.observe(el);
    return () => io.disconnect();
  });

  function run(target) {
    if (target == null || Number.isNaN(target)) {
      played = true;
      return;
    }
    const start = performance.now();
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      display = eased * target;
      if (t < 1) requestAnimationFrame(tick);
      else {
        display = target;
        played = true;
      }
    };
    requestAnimationFrame(tick);
  }
</script>

<span bind:this={el}>{format(display)}</span>
