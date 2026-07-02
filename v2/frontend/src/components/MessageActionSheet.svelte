<script>
  export let open = false
  export let canEdit = false
  export let canDelete = false
  export let canRegenerate = false

  import { createEventDispatcher } from 'svelte'
  const dispatch = createEventDispatcher()

  function pick(action) {
    dispatch('action', { action })
    open = false
  }

  function close() {
    open = false
    dispatch('close')
  }
</script>

{#if open}
  <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
  <div class="backdrop" on:click={close}></div>
  <div class="sheet" role="menu">
    <div class="handle"></div>
    {#if canEdit}
      <button type="button" class="item" on:click={() => pick('edit')}>✏️ 编辑消息</button>
    {/if}
    {#if canRegenerate}
      <button type="button" class="item" on:click={() => pick('regenerate')}>🔄 重新生成回复</button>
    {/if}
    {#if canDelete}
      <button type="button" class="item danger" on:click={() => pick('delete')}>🗑️ 删除消息</button>
    {/if}
    <button type="button" class="item cancel" on:click={close}>取消</button>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
    z-index: 150;
  }

  .sheet {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    background: var(--bg-secondary);
    border-top: 1px solid var(--border);
    border-radius: 16px 16px 0 0;
    padding: 8px 12px calc(12px + env(safe-area-inset-bottom, 0));
    z-index: 151;
    animation: slideUp 0.25s ease-out;
  }

  .handle {
    width: 36px;
    height: 4px;
    background: var(--border);
    border-radius: 2px;
    margin: 4px auto 12px;
  }

  .item {
    display: block;
    width: 100%;
    text-align: left;
    padding: 14px 16px;
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border-radius: var(--radius-sm);
    font-size: 0.95rem;
    margin-bottom: 8px;
  }

  .item.danger {
    color: var(--danger);
  }

  .item.cancel {
    background: transparent;
    color: var(--text-muted);
    text-align: center;
    margin-bottom: 0;
  }
</style>
