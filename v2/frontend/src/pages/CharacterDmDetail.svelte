<script>
  import { onMount } from 'svelte'
  import { createEventDispatcher } from 'svelte'
  import { apiUrl } from '../lib/api.js'
  import { formatWorldTime } from '../lib/timestamp.js'
  import CharacterAvatar from '../components/CharacterAvatar.svelte'
  import { characters, avatarUrlFor } from '../stores/characters.js'

  export let conversationId = ''

  const dispatch = createEventDispatcher()

  let detail = null
  let loading = true
  let error = ''

  async function loadDetail() {
    if (!conversationId) return
    loading = true
    error = ''
    try {
      const res = await fetch(apiUrl(`/api/v4/character-dm/${conversationId}`))
      if (!res.ok) throw new Error('加载失败')
      detail = await res.json()
    } catch (e) {
      error = e.message || '加载对话失败'
      detail = null
    } finally {
      loading = false
    }
  }

  $: if (conversationId) loadDetail()

  function goBack() {
    dispatch('back')
  }
</script>

<div class="dm-detail-page">
  <header class="page-header">
    <button type="button" class="back-btn" on:click={goBack} aria-label="返回">←</button>
    <div class="title-block">
      {#if detail?.conversation}
        <h2>{detail.conversation.character_a_name} × {detail.conversation.character_b_name}</h2>
        <p class="subtitle">角色私聊 · 只读旁观</p>
      {:else}
        <h2>角色私聊</h2>
      {/if}
    </div>
  </header>

  <div class="readonly-banner" role="note">
    此对话为角色私聊，你只能旁观，不能回复。
  </div>

  {#if loading}
    <div class="hint">加载中…</div>
  {:else if error}
    <div class="hint error">{error}</div>
  {:else if detail?.messages?.length}
    <div class="messages">
      {#each detail.messages as msg (msg.id)}
        <div class="msg-row">
          <CharacterAvatar
            characterId={msg.speaker_id}
            avatarUrl={avatarUrlFor(msg.speaker_id, $characters)}
            size={32}
            showStatus={false}
          />
          <div class="bubble-wrap">
            <span class="speaker">{msg.speaker_name}</span>
            <div class="bubble">{msg.content}</div>
            <span class="time">{formatWorldTime(msg.timestamp)}</span>
          </div>
        </div>
      {/each}
    </div>
  {:else}
    <div class="hint">暂无消息</div>
  {/if}

  <footer class="input-disabled">
    <div class="fake-input">旁观模式 — 无法回复</div>
  </footer>
</div>

<style>
  .dm-detail-page {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--bg-primary);
  }

  .page-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 14px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-secondary);
  }

  .back-btn {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: var(--bg-tertiary);
    color: var(--text-primary);
    font-size: 1.1rem;
  }

  .title-block h2 {
    margin: 0;
    font-size: 0.95rem;
  }

  .subtitle {
    margin: 2px 0 0;
    font-size: 0.72rem;
    color: var(--text-muted);
  }

  .readonly-banner {
    margin: 10px 14px 0;
    padding: 10px 12px;
    border-radius: 10px;
    background: rgba(251, 191, 36, 0.12);
    border: 1px solid rgba(251, 191, 36, 0.35);
    color: #fcd34d;
    font-size: 0.78rem;
    text-align: center;
  }

  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .msg-row {
    display: flex;
    gap: 10px;
    align-items: flex-start;
  }

  .bubble-wrap {
    display: flex;
    flex-direction: column;
    gap: 4px;
    max-width: 82%;
  }

  .speaker {
    font-size: 0.72rem;
    color: var(--text-muted);
    font-weight: 600;
  }

  .bubble {
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: 14px 14px 14px 4px;
    padding: 10px 14px;
    font-size: 0.88rem;
    line-height: 1.55;
  }

  .time {
    font-size: 0.65rem;
    color: var(--text-muted);
  }

  .hint {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
  }

  .hint.error { color: #fca5a5; }

  .input-disabled {
    padding: 12px 14px calc(12px + env(safe-area-inset-bottom, 0));
    border-top: 1px solid var(--border);
    background: var(--bg-secondary);
  }

  .fake-input {
    padding: 12px 14px;
    border-radius: 12px;
    background: var(--bg-tertiary);
    border: 1px dashed var(--border);
    color: var(--text-muted);
    font-size: 0.82rem;
    text-align: center;
  }
</style>
