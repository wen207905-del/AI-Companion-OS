<script>
  import { characters } from '../stores/characters.js'
  import { activeCharacterId } from '../stores/chat.js'
  import CharacterPanel from './CharacterPanel.svelte'

  /** When set from parent, overrides the picker. */
  export let initialId = null

  let selectedId = null

  $: if (initialId) {
    selectedId = initialId
  }
  $: if ($activeCharacterId) {
    selectedId = $activeCharacterId
  }
  $: if (!selectedId && $characters.length) {
    selectedId = $characters[0].id
  }
  $: current = $characters.find(c => c.id === selectedId)
</script>

<div class="mobile-detail">
  <header class="detail-header">
    <label class="picker-label" for="char-detail-select">查看角色</label>
    <select id="char-detail-select" class="char-select" bind:value={selectedId}>
      {#each $characters as char (char.id)}
        <option value={char.id}>{char.name} · {char.stage_name || '陌生人'}</option>
      {/each}
    </select>
    {#if current}
      <p class="hint">{current.name} · {current.occupation || current.type || '—'} · 好感 {current.love ?? 0} · 发情 {current.arousal ?? 0}{current.arousal_label ? `·${current.arousal_label}` : ''} · {current.mood || '平静'}</p>
    {/if}
  </header>

  {#if selectedId}
    <div class="panel-wrap">
      <CharacterPanel characterId={selectedId} />
    </div>
  {:else}
    <p class="empty">暂无角色数据</p>
  {/if}
</div>

<style>
  .mobile-detail {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    background: var(--bg-primary);
  }

  .detail-header {
    flex-shrink: 0;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-secondary);
  }

  .picker-label {
    display: block;
    font-size: 0.72rem;
    color: var(--text-muted);
    margin-bottom: 6px;
  }

  .char-select {
    width: 100%;
    padding: 10px 12px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    font-size: 0.9rem;
  }

  .hint {
    margin: 8px 0 0;
    font-size: 0.75rem;
    color: var(--text-secondary);
  }

  .panel-wrap {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
  }

  .empty {
    padding: 32px;
    text-align: center;
    color: var(--text-muted);
  }
</style>
