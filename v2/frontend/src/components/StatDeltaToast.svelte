<script>
  export let chips = []
  export let visible = false

  let hideTimer = null

  $: if (visible && chips.length) {
    if (hideTimer) clearTimeout(hideTimer)
    hideTimer = setTimeout(() => {
      visible = false
    }, 4500)
  }

  import { onDestroy } from 'svelte'
  onDestroy(() => {
    if (hideTimer) clearTimeout(hideTimer)
  })
</script>

{#if visible && chips.length}
  <div class="stat-toast" role="status">
    <span class="toast-title">数值变化</span>
    <div class="chips">
      {#each chips as chip}
        <span class="chip" class:up={chip.delta > 0} class:down={chip.delta < 0}>
          {chip.label} {chip.delta > 0 ? '+' : ''}{chip.delta.toFixed(1)}
        </span>
      {/each}
    </div>
  </div>
{/if}

<style>
  .stat-toast {
    position: absolute;
    left: 12px;
    right: 12px;
    top: 8px;
    z-index: 30;
    background: rgba(15, 23, 42, 0.92);
    border: 1px solid rgba(124, 92, 252, 0.45);
    border-radius: var(--radius);
    padding: 10px 12px;
    box-shadow: var(--shadow);
    animation: slideIn 0.3s ease;
  }

  @keyframes slideIn {
    from { transform: translateY(-8px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }

  .toast-title {
    display: block;
    font-size: 0.68rem;
    color: var(--text-muted);
    margin-bottom: 6px;
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .chip {
    font-size: 0.72rem;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 8px;
    font-variant-numeric: tabular-nums;
  }

  .chip.up {
    color: var(--success);
    background: rgba(52, 211, 153, 0.15);
  }

  .chip.down {
    color: var(--danger);
    background: rgba(248, 113, 113, 0.12);
  }
</style>
