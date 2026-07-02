<script>
  export let open = false
  export let title = '确认删除'
  export let message = '删除后无法恢复，确定继续吗？'
  export let confirmLabel = '删除'
  export let cancelLabel = '取消'
  export let danger = true

  import { createEventDispatcher } from 'svelte'
  const dispatch = createEventDispatcher()

  function close() {
    dispatch('cancel')
  }

  function confirm() {
    dispatch('confirm')
  }
</script>

{#if open}
  <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
  <div class="backdrop" on:click={close}></div>
  <div class="dialog" role="alertdialog" aria-modal="true">
    <h3 class="title">{title}</h3>
    <p class="message">{message}</p>
    <div class="actions">
      <button type="button" class="btn cancel" on:click={close}>{cancelLabel}</button>
      <button type="button" class="btn confirm" class:danger on:click={confirm}>{confirmLabel}</button>
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.55);
    z-index: 200;
  }

  .dialog {
    position: fixed;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    width: min(92vw, 360px);
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 20px;
    z-index: 201;
    animation: fadeIn 0.2s ease-out;
  }

  .title {
    font-size: 1rem;
    margin-bottom: 8px;
  }

  .message {
    font-size: 0.88rem;
    color: var(--text-secondary);
    line-height: 1.5;
    margin-bottom: 18px;
  }

  .actions {
    display: flex;
    gap: 10px;
    justify-content: flex-end;
  }

  .btn {
    padding: 8px 16px;
    border-radius: var(--radius-sm);
    font-size: 0.88rem;
    font-weight: 600;
  }

  .cancel {
    background: var(--bg-tertiary);
    color: var(--text-secondary);
  }

  .confirm {
    background: var(--accent);
    color: white;
  }

  .confirm.danger {
    background: var(--danger);
  }
</style>
