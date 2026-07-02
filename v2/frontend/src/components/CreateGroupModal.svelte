<script>
  import { createEventDispatcher } from 'svelte'
  import CharacterPicker from './CharacterPicker.svelte'

  const dispatch = createEventDispatcher()

  export let characters = []
  export let open = false

  let name = ''
  let selected = []
  let error = ''
  let saving = false
  let wasOpen = false

  /** 仅在弹窗刚打开时默认勾选前两人，不覆盖用户后续选择 */
  $: if (open && !wasOpen) {
    wasOpen = true
    name = ''
    error = ''
    selected = characters.length ? characters.slice(0, 2).map(c => c.id) : []
  }
  $: if (!open) wasOpen = false

  function close() {
    open = false
    error = ''
    name = ''
    selected = []
    dispatch('close')
  }

  async function submit() {
    error = ''
    if (selected.length < 1) {
      error = '请至少选择一名角色'
      return
    }
    saving = true
    try {
      const group = await import('../stores/characters.js').then(m =>
        m.createGroup(name.trim() || '新群聊', selected)
      )
      close()
      dispatch('created', group)
    } catch (e) {
      error = e.message || '创建失败'
    } finally {
      saving = false
    }
  }
</script>

{#if open}
  <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
  <div class="overlay" on:click|self={close}>
    <div class="modal">
      <header class="modal-header">
        <h3>新建群聊</h3>
        <button type="button" class="close-btn" on:click={close}>×</button>
      </header>

      <label class="field">
        <span>群名称</span>
        <input type="text" placeholder="例如：闺蜜下午茶" bind:value={name} />
      </label>

      <p class="hint">选择要一起聊天的角色（至少 1 人）</p>
      <CharacterPicker characters={characters} bind:selected min={1} />

      {#if error}
        <p class="error">{error}</p>
      {/if}

      <footer class="modal-footer">
        <button type="button" class="btn ghost" on:click={close}>取消</button>
        <button type="button" class="btn primary" disabled={saving} on:click={submit}>
          {saving ? '创建中…' : '创建并进入'}
        </button>
      </footer>
    </div>
  </div>
{/if}

<style>
  .overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.55);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 200;
    padding: 16px;
  }

  .modal {
    width: 100%;
    max-width: 420px;
    max-height: 90vh;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    animation: slideUp 0.25s ease-out;
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .modal-header h3 { font-size: 1.05rem; }

  .close-btn {
    background: transparent;
    color: var(--text-muted);
    font-size: 1.4rem;
    line-height: 1;
    padding: 4px 8px;
  }

  .field span {
    display: block;
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-bottom: 6px;
  }

  .field input {
    width: 100%;
    padding: 10px 12px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    font-size: 0.9rem;
  }

  .hint {
    font-size: 0.78rem;
    color: var(--text-muted);
  }

  .error {
    color: var(--danger);
    font-size: 0.82rem;
  }

  .modal-footer {
    display: flex;
    gap: 10px;
    justify-content: flex-end;
    margin-top: 4px;
  }

  .btn {
    padding: 10px 16px;
    border-radius: var(--radius-sm);
    font-size: 0.88rem;
    font-weight: 500;
  }

  .btn.ghost {
    background: var(--bg-tertiary);
    color: var(--text-secondary);
  }

  .btn.primary {
    background: var(--accent);
    color: white;
  }

  .btn:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
