// Tiny IntersectionObserver-backed Svelte action for scrollytelling steps.
// Usage:  <div use:inView={{ onEnter, onExit, threshold: 0.5 }}>
// onEnter and onExit get the element. We use rootMargin to bias activation
// so the active step is around the center of the viewport, which feels right
// for stepper UIs.

export function inView(node, params = {}) {
  const {
    onEnter,
    onExit,
    threshold = 0.55,
    rootMargin = '-30% 0px -30% 0px'
  } = params;

  const io = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) onEnter?.(node);
        else onExit?.(node);
      }
    },
    { threshold, rootMargin }
  );

  io.observe(node);

  return {
    destroy() {
      io.disconnect();
    }
  };
}

// Simple "fade in once it's reached" helper — sets a CSS class.
export function revealOnView(node, { className = 'is-visible', threshold = 0.2 } = {}) {
  const io = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          node.classList.add(className);
          io.disconnect();
          break;
        }
      }
    },
    { threshold }
  );
  io.observe(node);
  return {
    destroy() {
      io.disconnect();
    }
  };
}
