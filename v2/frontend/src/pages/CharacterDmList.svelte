<script>
  import { onMount, createEventDispatcher } from 'svelte'
  import { apiUrl } from '../lib/api.js'
  import { formatWorldTime } from '../lib/timestamp.js'
  import CharacterAvatar from '../components/CharacterAvatar.svelte'
  import { characters, avatarUrlFor } from '../stores/characters.js'
  import { dmListVersion } from '../stores/chat.js'

  const dispatch = createEventDispatcher()

  let conversations = []
  let loading = true
  let error = ''

  async function loadList() {
    loading = true
    error = ''
    try {
      const res = await fetch(apiUrl('/api/v4/character-dm/list'))
      if (!res.ok) throw new Error('加载失败')
      const data = await res.json()
      conversations = data.conversations || []
    } catch (e) {
      error = e.message || '加载角色私聊失败'
    } finally {
      loading = false
    }
  }

  onMount(loadList)

  $: if ($dmListVersion > 0) {
    loadList()
  }

  function openConversation(id) {
    dispatch('select', { id })
  }

  function triggerLabel(type) {
    const map = {
      jealousy_conflict: '嫉妒冲突',
      jealousy_probe: '试探吃醋',
      shared_scene: '同场后续',
      care_check: '关心打听',
      daily_chat: '日常闲聊',
      world_event: '世界事件',
    }
    return map[type] || type
  }
</script>

<div class="dm-list-page">
  <header class="page-header">
    <h2>角色私聊</h2>
    <p class="subtitle">角色之间的私下对话，你只能旁观</p>
  </header>

  {#if loading}
    <div class="hint">加载中…</div>
  {:else if error}
    <div class="hint error">{error}</div>
  {:else if conversations.length === 0}
    <div class="empty">
      <div class="empty-icon">🕸️</div>
      <p>还没有角色私聊记录</p>
      <p class="empty-sub">当角色因嫉妒、同场或日常原因私下对话时，会出现在这里</p>
    </div>
  {:else}
    <div class="conv-list">
      {#each conversations as conv (conv.id)}
        <button type="button" class="conv-item" on:click={() => openConversation(conv.id)}>
          <div class="avatars">
            <CharacterAvatar
              characterId={conv.character_a}
              avatarUrl={avatarUrlFor(conv.character_a, $characters)}
              size={34}
              showStatus={false}
            />
            <CharacterAvatar
              characterId={conv.character_b}
              avatarUrl={avatarUrlFor(conv.character_b, $characters)}
              size={34}
              showStatus={false}
            />
          </div>
          <div class="conv-body">
            <div class="conv-title">
              {conv.character_a_name} × {conv.character_b_name}
            </div>
            <div class="conv-meta">
              <span class="tag">{triggerLabel(conv.trigger_type)}</span>
              <span class="time">{formatWorldTime(conv.last_message_at)}</span>
            </div>
            {#if conv.preview}
              <p class="preview">{conv.preview}</p>
            {/if}
          </div>
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .dm-list-page {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--bg-primary);
  }

  .page-header {
    padding: 16px 18px 12px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-secondary);
  }

  .page-header h2 {
    margin: 0;
    font-size: 1.05rem;
  }

  .subtitle {
    margin: 4px 0 0;
    font-size: 0.78rem;
    color: var(--text-muted);
  }

  .hint {
    padding: 24px;
    text-align: center;
    color: var(--text-muted);
  }

  .hint.error { color: #fca5a5; }

  .empty {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 32px;
    text-align: center;
    color: var(--text-secondary);
  }

  .empty-icon { font-size: 2.5rem; opacity: 0.6; }
  .empty-sub { font-size: 0.82rem; color: var(--text-muted); max-width: 280px; }

  .conv-list {
    flex: 1;
    overflow-y: auto;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .conv-item {
    display: flex;
    gap: 12px;
    width: 100%;
    text-align: left;
    padding: 12px;
    border-radius: 12px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    color: inherit;
  }

  .conv-item:hover {
    border-color: rgba(124, 92, 252, 0.45);
    background: rgba(124, 92, 252, 0.06);
  }

  .avatars {
    display: flex;
    gap: -8px;
    flex-shrink: 0;
  }

  .avatars :global(.avatar-wrapper + .avatar-wrapper) {
    margin-left: -10px;
  }

  .conv-body { min-width: 0; flex: 1; }

  .conv-title {
    font-weight: 600;
    font-size: 0.92rem;
    margin-bottom: 4px;
  }

  .conv-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.72rem;
    color: var(--text-muted);
    margin-bottom: 6px;
  }

  .tag {
    background: rgba(124, 92, 252, 0.15);
    color: var(--accent-light);
    padding: 2px 8px;
    border-radius: 999px;
  }

  .preview {
    margin: 0;
    font-size: 0.82rem;
    color: var(--text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
