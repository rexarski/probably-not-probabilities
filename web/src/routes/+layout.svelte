<script>
  import '../styles/global.css';
  import 'katex/dist/katex.min.css';
  let { children } = $props();
</script>

<div class="scroll-progress" aria-hidden="true"></div>
{@render children()}

<style>
  .scroll-progress {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: var(--green, #1db954);
    transform: scaleX(0);
    transform-origin: 0 50%;
    z-index: 100;
    pointer-events: none;
    opacity: 0;
  }
  @supports (animation-timeline: scroll()) {
    .scroll-progress {
      opacity: 1;
      animation: scroll-progress linear forwards;
      animation-timeline: scroll(root block);
    }
  }
  @keyframes scroll-progress {
    to { transform: scaleX(1); }
  }
  @media (prefers-reduced-motion: reduce) {
    .scroll-progress { display: none; }
  }
</style>
