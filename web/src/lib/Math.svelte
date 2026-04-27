<script>
  import katex from 'katex';

  let { tex, display = false } = $props();

  let el = $state();

  $effect(() => {
    if (!el) return;
    katex.render(tex, el, {
      throwOnError: false,
      displayMode: display,
      output: 'html',
      strict: 'ignore'
    });
  });
</script>

{#if display}
  <div class="formula-katex" bind:this={el} aria-label={tex}></div>
{:else}
  <span class="inline-katex" bind:this={el} aria-label={tex}></span>
{/if}

<style>
  .formula-katex {
    background: var(--bg-alt);
    border-left: 3px solid var(--green);
    padding: 16px 22px;
    margin: 18px 0;
    color: var(--ink);
    overflow-x: auto;
  }
  .formula-katex :global(.katex) {
    font-size: 1.05em;
  }
  .formula-katex :global(.katex-display) {
    margin: 0;
    text-align: left;
  }
  .inline-katex :global(.katex) {
    color: var(--green-soft);
    font-size: 0.98em;
  }
</style>
