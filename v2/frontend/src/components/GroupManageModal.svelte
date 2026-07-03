<script>
  import { createEventDispatcher } from 'svelte'
  import CharacterAvatar from './CharacterAvatar.svelte'
  import CharacterPicker from './CharacterPicker.svelte'
  import ConfirmDialog from './ConfirmDialog.svelte'

  const dispatch = createEventDispatcher()

  export let open = false
  export let group = null
  export let characters = []

  let adding = false
  let toAdd = []
  let error = ''
  let busy = false
  let showDeleteConfirm = false

  $: members = group?.members || []
  $: memberChars = characters.filter(c => members.includes(c.id))
  $: availableToAdd = characters.filter(c => !members.includes(c.id))

  function close() {
    open = false
    adding = false
    toAdd = []
    error = ''
  }

  async function remove(charId) {
    if (members.length <= 1) {
      error = '至少保留一名成员'
      return
    }
    busy = true
    error = ''
    try {
      const updated = await import('../stores/characters.js').then(m =>
        m.removeGroupMember(group.id, charId)
      )
      dispatch('updated', updated)
    } catch (e) {
      error = e.message || '移除失败'
    } finally {
      busy = false
    }
  }

  async function confirmAdd() {
    if (!toAdd.length) return
    busy = true
    error = ''
    try {
      let updated = group
      const api = await import('../stores/characters.js')
      for (const id of toAdd) {
        updated = await api.addGroupMember(group.id, id)
      }
      adding = false
      toAdd = []
      dispatch('updated', updated)
    } catch (e) {
      error = e.message || '添加失败'
    } finally {
      busy = false
    }
  }

  async function deleteGroup() {
    showDeleteConfirm = true
  }

  async function confirmDeleteGroup() {
    showDeleteConfirm = false
    busy = true
    error = ''
    try {
      await import('../stores/characters.js').then(m => m.deleteGroup(group.id))
      close()
      dispatch('deleted', { id: group.id })
    } catch (e) {
      error = e.message || '删除失败'
    } finally {
      busy = false
    }
  }
</script>

{#if open && group}
  <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
  <div class="overlay" on:click|self={close}>
    <div class="modal">
      <header class="modal-header">
        <h3>群成员 · {group.name}</h3>
        <button type="button" class="close-btn" on:click={close}>×</button>
      </header>

      <div class="member-list">
        {#each memberChars as char (char.id)}
          <div class="member-row">
            <CharacterAvatar characterId={char.id} avatarUrl={char.avatar_url} size={36} showStatus={false} />
            <span class="member-name">{char.name}</span>
            <button
              type="button"
              class="remove-btn"
              disabled={busy || members.length <= 1}
              on:click={() => remove(char.id)}
            >移除</button>
          </div>
        {/each}
      </div>

      {#if adding}
        <p class="hint">选择要加入的角色</p>
        <CharacterPicker characters={availableToAdd} bind:selected={toAdd} min={0} />
        <div class="inline-actions">
          <button type="button" class="btn ghost" on:click={() => { adding = false; toAdd = [] }}>取消</button>
          <button type="button" class="btn primary" disabled={!toAdd.length || busy} on:click={confirmAdd}>确认添加</button>
        </div>
      {:else if availableToAdd.length}
        <button type="button" class="btn add-btn" disabled={busy} on:click={() => adding = true}>
          + 邀请角色入群
        </button>
      {/if}

      {#if error}
        <p class="error">{error}</p>
      {/if}

      <footer class="modal-footer">
        <button type="button" class="btn danger" disabled={busy} on:click={deleteGroup}>解散群聊</button>
      </footer>
    </div>
  </div>
{/if}

<ConfirmDialog
  open={showDeleteConfirm}
  title="解散该群聊？"
  message="历史消息将被永久删除，且手机与电脑上的列表都会同步更新。"
  confirmLabel="解散"
  on:confirm={confirmDeleteGroup}
  on:cancel={() => showDeleteConfirm = false}
/>

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
    overflow-y: auto;
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .close-btn {
    background: transparent;
    color: var(--text-muted);
    font-size: 1.4rem;
    padding: 4px 8px;
  }

  .member-list { display: flex; flex-direction: column; gap: 6px; }

  .member-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 10px;
    background: var(--bg-tertiary);
    border-radius: var(--radius-sm);
  }

  .member-name { flex: 1; font-size: 0.9rem; }

  .remove-btn {
    background: transparent;
    color: var(--danger);
    font-size: 0.78rem;
    padding: 4px 8px;
  }

  .remove-btn:disabled { opacity: 0.4; }

  .hint { font-size: 0.78rem; color: var(--text-muted); }

  .add-btn {
    width: 100%;
    padding: 10px;
    background: var(--bg-tertiary);
    color: var(--accent-light);
    border-radius: var(--radius-sm);
    font-size: 0.88rem;
  }

  .inline-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }

  .error { color: var(--danger); font-size: 0.82rem; }

  .modal-footer { margin-top: 8px; }

  .btn {
    padding: 8px 14px;
    border-radius: var(--radius-sm);
    font-size: 0.85rem;
  }

  .btn.ghost { background: var(--bg-tertiary); color: var(--text-secondary); }
  .btn.primary { background: var(--accent); color: white; }
  .btn.danger { background: transparent; color: var(--danger); border: 1px solid var(--danger); }
  .btn:disabled { opacity: 0.5; }
</style>
