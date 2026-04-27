<script>
  // A 6×4 mosaic of real album covers behind the hero. Each tile flips on
  // the Y-axis at staggered intervals (solari-board style) to swap between
  // two covers. A heavy radial overlay sits on top so the grid reads as
  // atmosphere — a flickering field of color — rather than as content.
  import { onMount } from 'svelte';
  import { loadCovers, dataPath } from '$lib/data.js';

  const COLS = 4;
  const ROWS = 8; // generated; vertical overflow is clipped at the hero edge
  const TILES = COLS * ROWS;

  /** @type {{ id: string, title: string, subtitle: string, file: string }[]} */
  let covers = $state([]);

  // Deterministic PRNG so the initial face assignment is stable across
  // SSR / hydrate (no flash of differently-laid-out grid).
  function rand(seed) {
    const x = Math.sin(seed * 9301 + 49297) * 233280;
    return x - Math.floor(x);
  }

  // Build the per-tile config from however many covers we have. Each tile
  // gets two faces (front + back). We sample without replacement within a
  // tile so a tile never flips to itself.
  const tiles = $derived.by(() => {
    if (!covers.length) return [];
    const out = [];
    for (let i = 0; i < TILES; i++) {
      const a = Math.floor(rand(i * 2 + 1) * covers.length);
      let b = Math.floor(rand(i * 2 + 2) * covers.length);
      if (b === a) b = (b + 1) % covers.length;
      out.push({
        id: i,
        a: covers[a],
        b: covers[b],
        delay: rand(i * 5 + 11) * 9,
        dur: 10 + rand(i * 7 + 3) * 6
      });
    }
    return out;
  });

  onMount(async () => {
    try {
      covers = await loadCovers();
    } catch (_e) {
      covers = [];
    }
  });
</script>

<div class="mosaic" aria-hidden="true" style="--cols: {COLS}; --rows: {ROWS};">
  {#each tiles as tile (tile.id)}
    <div class="tile" style="--delay: {tile.delay}s; --dur: {tile.dur}s;">
      <div class="face">
        <img src={dataPath(tile.a.file)} alt="" loading="lazy" decoding="async" />
      </div>
      <div class="face back">
        <img src={dataPath(tile.b.file)} alt="" loading="lazy" decoding="async" />
      </div>
    </div>
  {/each}
  <div class="overlay"></div>
</div>

<style>
  .mosaic {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    width: clamp(260px, 42%, 560px);
    display: grid;
    grid-template-columns: repeat(var(--cols), 1fr);
    grid-auto-rows: 1fr;
    gap: 3px;
    z-index: 0;
    pointer-events: none;
    perspective: 1400px;
    overflow: hidden;
    /* Soft fade on the left and bottom so the mosaic dissolves into bg
       instead of cutting off as a hard rectangle. */
    -webkit-mask-image:
      linear-gradient(to right, transparent 0%, black 22%, black 100%),
      linear-gradient(to bottom, black 0%, black 80%, transparent 100%);
    mask-image:
      linear-gradient(to right, transparent 0%, black 22%, black 100%),
      linear-gradient(to bottom, black 0%, black 80%, transparent 100%);
    -webkit-mask-composite: source-in;
    mask-composite: intersect;
  }
  .overlay {
    position: absolute;
    inset: 0;
    z-index: 2;
    background: rgba(13, 13, 13, 0.32);
    pointer-events: none;
  }
  .tile {
    position: relative;
    aspect-ratio: 1 / 1;
    transform-style: preserve-3d;
    animation: flip var(--dur) cubic-bezier(0.7, 0, 0.3, 1) infinite;
    animation-delay: var(--delay);
    will-change: transform;
  }
  .face {
    position: absolute;
    inset: 0;
    backface-visibility: hidden;
    overflow: hidden;
    background: #1a1a1a;
  }
  .face img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    /* desaturate slightly so the colors sit further back */
    filter: saturate(0.85) contrast(1.05);
  }
  .face.back {
    transform: rotateY(180deg);
  }
  /* Long static dwell on each face, fast flip in between. */
  @keyframes flip {
    0%, 46% { transform: rotateY(0deg); }
    52%, 96% { transform: rotateY(180deg); }
    100% { transform: rotateY(360deg); }
  }

  @media (max-width: 720px) {
    .mosaic {
      width: 60%;
      grid-template-columns: repeat(3, 1fr);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .tile {
      animation: none;
    }
  }
</style>
