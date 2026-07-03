<script>
  export let message = {}
  export let isUser = false
  export let userSenderLabel = ''
  export let disabled = false

  import { createEventDispatcher } from 'svelte'
  import MessageActionSheet from './MessageActionSheet.svelte'
  import ReplyContent from './ReplyContent.svelte'
  import CharacterAvatar from './CharacterAvatar.svelte'
  import { characters, avatarUrlFor } from '../stores/characters.js'
  import { hasActionSegments } from '../lib/replyFormat.js'
  import { formatWorldTime } from '../lib/timestamp.js'

  const dispatch = createEventDispatcher()

  let showMenu = false
  let showInnerThought = false
  let isEditing = false
  let editText = ''
  let longPressTimer = null

  $: contents = message.content || ''
  $: contentType = message.contentType || message.content_type || 'text'
  $: isImage = contentType === 'image'
  $: actionText = getActionText(message.action)
  $: innerThought = message.innerThought || ''
  $: thoughtLabel = characterName ? `${characterName}·内心` : '角色·内心'
  $: showInnerThoughtPanel = innerThought && !isSystemInnerThought(innerThought)

  function isSystemInnerThought(text) {
    if (!text) return true
    return /LLM|API|未配置|\.env|调用失败|超时/.test(text)
  }
  $: characterName = message.characterName || ''
  $: characterId = message.senderId || message.characterId || ''
  $: avatarUrl = message.avatarUrl || avatarUrlFor(characterId, $characters)
  $: time = formatTime(message.timestamp)
  $: isPending = !message.id || String(message.id).startsWith('local_')
  $: canEdit = isUser && !disabled && !message.isStreaming && !isPending
  $: canDelete = !disabled && !message.isStreaming && !isPending
  $: canRegenerate = !isUser && !disabled && !message.isStreaming && !isPending
  $: hasActions = canEdit || canDelete || canRegenerate
  $: showLegacyAction = actionText && !hasActionSegments(contents)

  function getActionText(action) {
    if (!action) return ''
    if (typeof action === 'string') return action
    if (typeof action === 'object' && action.type) {
      const ACTION_CN = {
        smile: '微笑', pout: '噘嘴', sleep: '困了', wave: '挥手',
        hesitate: '欲言又止', talk: '说道', nod: '点头', think: '思考中',
      }
      return ACTION_CN[action.type] || action.type
    }
    return ''
  }

  function formatTime(ts) {
    return formatWorldTime(ts)
  }

  function openMenu(e) {
    if (!hasActions) return
    e?.preventDefault?.()
    e?.stopPropagation?.()
    showMenu = true
  }

  function onTouchStart(e) {
    if (!hasActions) return
    clearTimeout(longPressTimer)
    longPressTimer = setTimeout(() => openMenu(e), 480)
  }

  function onTouchEnd() {
    clearTimeout(longPressTimer)
  }

  function onSheetAction(e) {
    const action = e.detail.action
    if (action === 'edit') {
      editText = contents
      isEditing = true
    } else if (action === 'delete') {
      dispatch('delete', { id: message.id })
    } else if (action === 'regenerate') {
      dispatch('regenerate', { id: message.id })
    }
  }

  function saveEdit() {
    const text = editText.trim()
    if (!text || text === contents) {
      isEditing = false
      return
    }
    dispatch('edit', { id: message.id, content: text })
    isEditing = false
  }

  function cancelEdit() {
    isEditing = false
    editText = contents
  }

  function onKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      saveEdit()
    }
    if (e.key === 'Escape') cancelEdit()
  }
</script>

<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
  class="message"
  class:isUser
  class:isBot={!isUser}
  on:contextmenu={openMenu}
  on:touchstart={onTouchStart}
  on:touchend={onTouchEnd}
  on:touchmove={onTouchEnd}
  on:touchcancel={onTouchEnd}
>
  {#if isUser}
    <div class="user-col">
      {#if userSenderLabel}
        <span class="user-sender-name">{userSenderLabel}</span>
      {/if}
    <div class="bubble user-bubble">
      {#if isEditing}
        <textarea
          class="edit-area"
          bind:value={editText}
          rows="3"
          on:keydown={onKeydown}
        ></textarea>
        <div class="edit-actions">
          <button type="button" class="mini-btn" on:click={cancelEdit}>取消</button>
          <button type="button" class="mini-btn primary" on:click={saveEdit}>保存</button>
        </div>
      {:else}
        <div class="bubble-content">{contents}</div>
        <div class="meta-row">
          {#if message.edited}<span class="edited-tag">已编辑</span>{/if}
          <span class="time user-time">{time}</span>
        </div>
      {/if}
      {#if hasActions && !isEditing}
        <button type="button" class="more-btn user-more" on:click={openMenu} aria-label="消息操作">⋯</button>
      {/if}
    </div>
    </div>
  {:else}
    <div class="bot-row">
      <div class="avatar-slot">
        {#if characterId && characterId !== 'user'}
          <CharacterAvatar {characterId} avatarUrl={avatarUrl} size={34} showStatus={false} />
        {:else}
          <div class="avatar-placeholder">{characterName?.[0] || '?'}</div>
        {/if}
      </div>
      <div class="bot-content">
        {#if characterName}
          <span class="bot-name">{characterName}</span>
        {/if}
        <div class="bubble bot-bubble">
          {#if showLegacyAction}
            <span class="action-text">*{actionText}*</span>
          {/if}
          <div class="bubble-content">
            {#if isImage}
              <img class="chat-photo" src={contents} alt="角色照片" loading="lazy" />
            {:else}
              <ReplyContent content={contents} streaming={message.isStreaming} />
            {/if}
          </div>
          {#if hasActions}
            <button type="button" class="more-btn bot-more" on:click={openMenu} aria-label="消息操作">⋯</button>
          {/if}
          {#if canRegenerate}
            <button
              type="button"
              class="regen-btn"
              title="重新生成这条回复"
              aria-label="重新生成"
              on:click={() => dispatch('regenerate', { id: message.id })}
            >↻</button>
          {/if}
        </div>

        {#if showInnerThoughtPanel}
          <button type="button" class="thought-toggle" on:click={() => showInnerThought = !showInnerThought}>
            💜 {showInnerThought ? '收起内心' : `查看${thoughtLabel}`}
          </button>
          {#if showInnerThought}
            <div class="inner-thought">
              <span class="thought-label">{thoughtLabel}</span>
              <span class="thought-hint">角色私密想法，不是你的心声</span>
              <span class="thought-text">{innerThought}</span>
            </div>
          {/if}
        {/if}

        <div class="meta-row">
          {#if message.edited}<span class="edited-tag">已编辑</span>{/if}
          <span class="time">{time}</span>
        </div>
      </div>
    </div>
  {/if}
</div>

<MessageActionSheet
  bind:open={showMenu}
  {canEdit}
  {canDelete}
  {canRegenerate}
  on:action={onSheetAction}
/>

<style>
  .message {
    display: flex;
    animation: fadeIn 0.3s ease-out;
    position: relative;
  }

  .message.isUser { justify-content: flex-end; }

  .user-col {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 4px;
    max-width: 72%;
  }

  .user-sender-name {
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--accent-light);
    padding-right: 4px;
  }

  .user-bubble {
    position: relative;
    background: linear-gradient(135deg, var(--accent), var(--accent-blue));
    color: white;
    width: 100%;
    max-width: 100%;
    padding: 10px 16px;
    border-radius: 16px 16px 4px 16px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .meta-row {
    display: flex;
    align-items: center;
    gap: 6px;
    justify-content: flex-end;
  }

  .edited-tag {
    font-size: 0.65rem;
    opacity: 0.75;
  }

  .user-time {
    font-size: 0.7rem;
    opacity: 0.7;
  }

  .bot-row {
    display: flex;
    gap: 10px;
    max-width: 94%;
  }

  .avatar-slot {
    flex-shrink: 0;
    width: 34px;
    height: 34px;
  }

  .avatar-placeholder {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--bg-tertiary), var(--border));
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-secondary);
    font-weight: 600;
    font-size: 0.8rem;
    flex-shrink: 0;
    border: 2px solid var(--border);
  }

  .bot-content {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .bot-name {
    font-size: 0.8rem;
    color: var(--text-muted);
    font-weight: 600;
  }

  .bot-bubble {
    position: relative;
    background: var(--bg-tertiary);
    color: var(--text-primary);
    padding: 10px 16px;
    border-radius: 16px 16px 16px 4px;
    border: 1px solid var(--border);
  }

  .bubble-content {
    font-size: 0.9rem;
    line-height: 1.6;
    word-break: break-word;
    padding-right: 18px;
  }

  .chat-photo {
    display: block;
    max-width: min(280px, 72vw);
    max-height: 420px;
    border-radius: 12px;
    object-fit: cover;
    border: 1px solid rgba(255, 255, 255, 0.08);
  }

  .stream-cursor {
    display: none;
  }

  .action-text {
    display: block;
    font-style: italic;
    color: #fbbf24;
    margin-bottom: 6px;
    font-size: 0.85rem;
  }

  .time {
    font-size: 0.7rem;
    color: var(--text-muted);
  }

  .thought-toggle {
    font-size: 0.72rem;
    background: rgba(192, 132, 252, 0.14);
    color: #e9d5ff;
    cursor: pointer;
    text-align: left;
    padding: 4px 10px;
    border-radius: 10px;
    border: 1px solid rgba(192, 132, 252, 0.35);
  }

  .inner-thought {
    background: rgba(88, 28, 135, 0.18);
    border: 1px solid rgba(192, 132, 252, 0.35);
    border-left: 3px solid #c084fc;
    border-radius: var(--radius-sm);
    padding: 10px 12px;
    font-size: 0.82rem;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .thought-label {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    color: #d8b4fe;
    text-transform: uppercase;
  }

  .thought-hint {
    font-size: 0.62rem;
    color: rgba(243, 232, 255, 0.55);
    font-style: normal;
  }

  .thought-text {
    color: #f3e8ff;
    line-height: 1.65;
    font-style: italic;
  }

  .more-btn {
    position: absolute;
    top: 6px;
    right: 6px;
    width: 24px;
    height: 24px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.15);
    color: inherit;
    font-size: 1rem;
    line-height: 1;
    opacity: 0;
    transition: opacity 0.15s;
  }

  .user-bubble .more-btn {
    background: rgba(0, 0, 0, 0.15);
  }

  .message:hover .more-btn,
  .more-btn:focus {
    opacity: 1;
  }

  .regen-btn {
    position: absolute;
    top: 6px;
    right: 32px;
    width: 24px;
    height: 24px;
    border-radius: 12px;
    background: rgba(124, 92, 252, 0.2);
    color: var(--accent-light);
    font-size: 0.95rem;
    line-height: 1;
    opacity: 0;
    transition: opacity 0.15s;
  }

  .message:hover .regen-btn,
  .regen-btn:focus {
    opacity: 1;
  }

  @media (max-width: 768px) {
    .regen-btn { opacity: 0.85; }
  }

  .edit-area {
    width: 100%;
    min-width: 200px;
    background: rgba(255, 255, 255, 0.12);
    color: white;
    border-radius: var(--radius-sm);
    padding: 8px;
    font-size: 0.9rem;
    line-height: 1.5;
    resize: vertical;
  }

  .edit-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }

  .mini-btn {
    padding: 4px 12px;
    border-radius: 8px;
    font-size: 0.78rem;
    background: rgba(255, 255, 255, 0.2);
    color: white;
  }

  .mini-btn.primary {
    background: white;
    color: var(--accent);
    font-weight: 600;
  }

  @media (max-width: 768px) {
    .more-btn { opacity: 0.85; }
    .user-bubble { max-width: 85%; }
    .bot-row { max-width: 96%; }
  }
</style>
