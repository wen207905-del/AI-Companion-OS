<script>
  import { onDestroy, tick, createEventDispatcher } from 'svelte'
  import {
    messages,
    connectionStatus,
    isWaitingReply,
    isLoadingHistory,
    typingCharacters,
    isStreamingReply,
    activeGroup,
  } from '../stores/chat.js'
  import { currentLlm, providers } from '../stores/llm.js'
  import { characters, groups, loadCharacterDetail, userProfile } from '../stores/characters.js'
  import { lastPrivateMsgTimestamp, lastStatUpdate } from '../stores/chat.js'
  import MessageBubble from '../components/MessageBubble.svelte'
  import ChatInput from '../components/ChatInput.svelte'
  import LlmSelector from '../components/LlmSelector.svelte'
  import CharacterAvatar from '../components/CharacterAvatar.svelte'
  import { avatarUrlFor } from '../stores/characters.js'
  import GroupManageModal from '../components/GroupManageModal.svelte'
  import ConfirmDialog from '../components/ConfirmDialog.svelte'
  import GroupGameHintsPanel from '../components/GroupGameHintsPanel.svelte'
  import GroupMemberChips from '../components/GroupMemberChips.svelte'
  import StatDeltaToast from '../components/StatDeltaToast.svelte'
  import { editMessage, deleteMessage, regenerateReply } from '../stores/chat.js'
  import { worldClockLabel, worldLocationLabel } from '../stores/worldTime.js'
  import { formatStatusLine, formatCharacterProfileLine, formatCharacterStatsLine, formatGroupProfileLine, formatGroupStatsLine } from '../lib/labels.js'
  import { formatStatDeltaChips } from '../lib/statLabels.js'

  export let view
  export let characterId = null
  export let groupId = null
  export let onMenuClick = null

  const dispatch = createEventDispatcher()

  let messagesContainer
  let lastMsgCount = 0
  let showGroupManage = false
  let pendingDeleteId = null
  let showDeleteConfirm = false
  let charDetail = null
  let charStatusTimer = null
  let chatInputEl
  let hintsExpanded = false
  let hintsAutoExpandedFor = ''
  let lastHintsGroupId = ''
  let statToastVisible = false
  let statToastChips = []
  let lastStatToastTs = 0

  function groupHintsStorageKey(gid) {
    return `group_hints_expanded_${gid || 'default'}`
  }

  function readHintsExpandedPref(gid) {
    try {
      const saved = localStorage.getItem(groupHintsStorageKey(gid))
      if (saved === '0') return false
      if (saved === '1') return true
    } catch (_) {
      /* ignore */
    }
    return null
  }

  $: if (groupId !== lastHintsGroupId) {
    lastHintsGroupId = groupId || ''
    hintsAutoExpandedFor = ''
  }

  /* 空群仅自动展开一次；用户收起后不再强制弹开（含 localStorage 记忆） */
  $: if (view === 'group' && groupId && $messages.length === 0 && !$isLoadingHistory) {
    const autoKey = `${groupId}:empty`
    if (hintsAutoExpandedFor !== autoKey) {
      hintsAutoExpandedFor = autoKey
      const pref = readHintsExpandedPref(groupId)
      hintsExpanded = pref === null ? true : pref
    }
  }

  async function refreshCharStatus(id) {
    if (view !== 'private' || !id) {
      charDetail = null
      return
    }
    const d = await loadCharacterDetail(id)
    if (view === 'private' && characterId === id) {
      charDetail = d
    }
  }

  $: if (view === 'private' && characterId) {
    refreshCharStatus(characterId)
  } else {
    charDetail = null
  }

  $: if (view === 'private' && characterId && $lastStatUpdate?.characterId === characterId
    && $lastStatUpdate.ts !== lastStatToastTs) {
    lastStatToastTs = $lastStatUpdate.ts
    const payload = $lastStatUpdate
    charDetail = {
      ...(charDetail || {}),
      relationship: payload.relationship || charDetail?.relationship,
      emotion: payload.emotion || charDetail?.emotion,
      growth: payload.growth || charDetail?.growth,
      arousal: payload.arousal || charDetail?.arousal,
      persona: charDetail?.persona || {},
    }
    statToastChips = formatStatDeltaChips(payload.deltas)
    statToastVisible = statToastChips.length > 0
  }

  $: if (view === 'private' && characterId && $lastPrivateMsgTimestamp > 0) {
    if (charStatusTimer) clearTimeout(charStatusTimer)
    charStatusTimer = setTimeout(() => refreshCharStatus(characterId), 500)
  }

  $: statusProfileHint = view === 'private' && charDetail
    ? formatCharacterProfileLine(charDetail.persona)
    : view === 'group' && groupMembers.length
      ? formatGroupProfileLine(groupMembers, $characters)
      : ''

  $: statusStatsHint = view === 'private' && charDetail
    ? formatCharacterStatsLine({
        relationship: charDetail.relationship,
        emotion: charDetail.emotion,
        arousal: charDetail.arousal,
      })
    : view === 'group' && groupMembers.length
      ? formatGroupStatsLine(groupMembers, $characters)
      : ''

  $: userSenderLabel = view === 'group'
    ? ($userProfile.nickname || $userProfile.name || '我')
    : ''

  $: scopeType = view === 'group' ? 'group' : 'private'
  $: scopeId = view === 'group' ? (groupId || '') : (characterId || '')
  $: currentCharName = $characters.find(c => c.id === characterId)?.name || ''
  $: groupName = $activeGroup?.name || '群聊'
  $: groupMembers = $activeGroup?.members || []
  $: groupMemberChips = groupMembers.map(id => {
    const c = $characters.find(x => x.id === id)
    return {
      id,
      name: c?.name || id,
      love: c?.love,
      arousal: c?.arousal,
      avatar_url: c?.avatar_url,
    }
  })
  $: chatTitle = view === 'group'
    ? groupName
    : currentCharName
  $: groupStatusLine = formatStatusLine({
    connection: $connectionStatus,
    waiting: $isWaitingReply,
    streaming: $isStreamingReply,
    llm: $currentLlm,
    providers: $providers,
    typingNames: $typingCharacters.map(c => c.name),
    profileHint: '',
    statsHint: '',
  })
  $: privateStatusText = formatStatusLine({
    connection: $connectionStatus,
    waiting: $isWaitingReply,
    streaming: $isStreamingReply,
    llm: $currentLlm,
    providers: $providers,
    typingNames: $typingCharacters.map(c => c.name),
    profileHint: statusProfileHint,
    statsHint: statusStatsHint,
  })
  $: statusText = view === 'group' ? groupStatusLine : privateStatusText
  $: typingHint = $isStreamingReply
    ? '正在输出回复…'
    : $typingCharacters.length
      ? `${$typingCharacters.map(c => c.name).join('、')} 正在输入…`
      : '正在思考回复…'
  $: showWaitingRow = ($isWaitingReply || $isStreamingReply) && !$isLoadingHistory
  $: msgDisabled = $isWaitingReply || $isStreamingReply

  $: if ($messages.length !== lastMsgCount) {
    lastMsgCount = $messages.length
    tick().then(() => {
      if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight
      }
    })
  }

  function onGroupHintSelect(e) {
    chatInputEl?.setDraft(e.detail)
  }

  function handleSend(content) {
    import('../stores/chat.js').then(m => m.sendMessage(content))
  }

  function onEditMessage(e) {
    editMessage(e.detail.id, e.detail.content)
  }

  function onDeleteRequest(e) {
    pendingDeleteId = e.detail.id
    showDeleteConfirm = true
  }

  function onRegenerateRequest(e) {
    regenerateReply(e.detail.id)
  }

  async function confirmDelete() {
    if (pendingDeleteId) {
      await deleteMessage(pendingDeleteId)
    }
    pendingDeleteId = null
    showDeleteConfirm = false
  }

  function cancelDelete() {
    pendingDeleteId = null
    showDeleteConfirm = false
  }

  function onGroupUpdated(e) {
    activeGroup.set(e.detail)
    groups.update(list =>
      list.map(g => (g.id === e.detail.id ? { ...g, member_count: e.detail.members?.length ?? g.member_count } : g))
    )
  }

  function onGroupDeleted(e) {
    showGroupManage = false
    dispatch('groupDeleted', e.detail)
  }

  onDestroy(() => {
    if (charStatusTimer) clearTimeout(charStatusTimer)
  })
</script>

<div class="chat-page" class:is-group={view === 'group'}>
  <header class="chat-header">
    <div class="header-row">
      <div class="header-left">
        {#if onMenuClick}
          <button type="button" class="menu-btn" on:click={onMenuClick} aria-label="菜单">☰</button>
        {/if}
        <div class="title-block">
          <div class="title-line">
            <span class="chat-type-badge">{view === 'group' ? '群聊' : '私聊'}</span>
            <h2 class="chat-title">{chatTitle}</h2>
          </div>
          {#if view === 'private'}
            {#if $worldClockLabel}
              <p class="meta-line">
                <span class="world-time">{$worldClockLabel}</span>
                <span class="meta-sep">·</span>
                <span class="world-loc">{$worldLocationLabel}</span>
              </p>
            {/if}
          {/if}
        </div>
      </div>
      <div class="header-right">
        {#if view === 'group' && groupId}
          <button type="button" class="members-btn" on:click={() => showGroupManage = true} aria-label="管理群成员">
            <span class="avatar-stack">
              {#each groupMembers.slice(0, 3) as mid (mid)}
                <CharacterAvatar
                  characterId={mid}
                  avatarUrl={avatarUrlFor(mid, $characters)}
                  size={26}
                  showStatus={false}
                />
              {/each}
            </span>
            <span class="members-label">{groupMembers.length}</span>
          </button>
        {/if}
        <LlmSelector {scopeType} {scopeId} />
      </div>
    </div>

    {#if view === 'group'}
      <div class="group-subbar">
        <div class="world-pill" title="{$worldLocationLabel}">
          <span class="world-pill-time">{$worldClockLabel || '--:--'}</span>
          <span class="world-pill-loc">{$worldLocationLabel}</span>
        </div>
        {#if groupMemberChips.length}
          <GroupMemberChips members={groupMemberChips} />
        {/if}
      </div>
    {/if}
  </header>

  <div class="messages-wrap">
    {#if view === 'private'}
      <StatDeltaToast chips={statToastChips} bind:visible={statToastVisible} />
    {/if}
  <div class="messages-container" bind:this={messagesContainer}>
    {#if $isLoadingHistory}
      <div class="loading-hint">加载历史消息…</div>
    {/if}

    {#each $messages as msg (msg.id)}
      {#if msg.type === 'system'}
        <div class="system-msg">{msg.content}</div>
      {:else}
        <MessageBubble
          message={msg}
          isUser={msg.senderType === 'user'}
          userSenderLabel={msg.senderType === 'user' ? userSenderLabel : ''}
          disabled={msgDisabled}
          on:edit={onEditMessage}
          on:delete={onDeleteRequest}
          on:regenerate={onRegenerateRequest}
        />
      {/if}
    {/each}

    {#if showWaitingRow && !$isStreamingReply}
      <div class="typing-row">
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-text">{typingHint}</span>
      </div>
    {/if}

    {#if !$isLoadingHistory && $messages.length === 0}
      <div class="empty-state">
        <div class="empty-icon">{view === 'group' ? '👥' : '💬'}</div>
        <p>{view === 'group' ? '群里还没有消息，招呼一下大家吧～' : '还没有消息，说点什么吧～'}</p>
        {#if view === 'group'}
          <p class="empty-sub">下方「群聊玩法提示」可查看游戏规则与示例开场</p>
        {/if}
      </div>
    {/if}
  </div>
  </div>

  {#if view === 'group' && groupId}
    <GroupGameHintsPanel
      {groupId}
      bind:expanded={hintsExpanded}
      on:select={onGroupHintSelect}
    />
  {/if}

  <ChatInput
    bind:this={chatInputEl}
    on:send={e => handleSend(e.detail)}
    disabled={$isWaitingReply || $isStreamingReply}
    compact={view === 'group'}
  />

  <footer class="status-bar" class:group-status={view === 'group'} class:waiting={$isWaitingReply || $isStreamingReply} class:offline={$connectionStatus !== 'connected'}>
    {statusText}
  </footer>
</div>

<GroupManageModal
  open={showGroupManage}
  group={$activeGroup}
  characters={$characters}
  on:updated={onGroupUpdated}
  on:deleted={onGroupDeleted}
/>

<ConfirmDialog
  open={showDeleteConfirm}
  title="删除这条消息？"
  message="删除后无法恢复。角色的记忆也会移除相关记录。"
  confirmLabel="删除"
  on:confirm={confirmDelete}
  on:cancel={cancelDelete}
/>

<style>
  .chat-page {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .chat-header {
    display: flex;
    flex-direction: column;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  .header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px;
    gap: 10px;
    min-width: 0;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    flex: 1;
  }

  .menu-btn {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    width: 36px;
    height: 36px;
    border-radius: var(--radius-sm);
    font-size: 1.1rem;
    flex-shrink: 0;
  }

  .chat-type-badge {
    background: var(--accent);
    color: white;
    font-size: 0.62rem;
    padding: 2px 6px;
    border-radius: 8px;
    font-weight: 600;
    flex-shrink: 0;
  }

  .title-block {
    min-width: 0;
    flex: 1;
  }

  .title-line {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
  }

  .chat-title {
    font-size: 0.95rem;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }

  .meta-line {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-top: 2px;
    font-size: 0.72rem;
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .world-time {
    color: var(--accent-light);
    font-variant-numeric: tabular-nums;
    font-weight: 600;
  }

  .meta-sep { opacity: 0.5; }

  .world-loc {
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .group-subbar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 14px 10px;
    min-width: 0;
  }

  .world-pill {
    display: inline-flex;
    flex-direction: row;
    align-items: center;
    gap: 5px;
    flex-shrink: 0;
    padding: 6px 10px;
    border-radius: 999px;
    background: rgba(124, 92, 252, 0.12);
    border: 1px solid rgba(124, 92, 252, 0.25);
    white-space: nowrap;
  }

  .world-pill-time {
    font-size: 0.8rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    color: var(--accent-light);
    line-height: 1;
  }

  .world-pill-loc {
    font-size: 0.68rem;
    color: var(--text-muted);
    max-width: 5.5em;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }

  .members-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    background: var(--bg-tertiary);
    padding: 4px 8px 4px 4px;
    border-radius: 999px;
    color: var(--text-secondary);
    font-size: 0.72rem;
    min-height: 36px;
  }

  .avatar-stack {
    display: flex;
    align-items: center;
  }

  .avatar-stack :global(.avatar-wrapper) {
    margin-left: -8px;
    border: 2px solid var(--bg-secondary);
    border-radius: 50%;
  }

  .avatar-stack :global(.avatar-wrapper:first-child) {
    margin-left: 0;
  }

  .members-label {
    font-weight: 600;
    color: var(--text-primary);
    min-width: 1ch;
  }

  .messages-wrap {
    position: relative;
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .messages-container {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    -webkit-overflow-scrolling: touch;
  }

  .loading-hint {
    text-align: center;
    color: var(--text-muted);
    font-size: 0.8rem;
    padding: 8px;
  }

  .system-msg {
    text-align: center;
    color: var(--text-muted);
    font-size: 0.75rem;
    padding: 4px 0;
  }

  .typing-row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 12px;
    color: var(--text-muted);
    font-size: 0.82rem;
  }

  .typing-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent-light);
    animation: typingBounce 1.2s ease-in-out infinite;
  }
  .typing-dot:nth-child(2) { animation-delay: 0.15s; }
  .typing-dot:nth-child(3) { animation-delay: 0.3s; }

  @keyframes typingBounce {
    0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
    30% { transform: translateY(-4px); opacity: 1; }
  }

  .empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    gap: 12px;
    padding: 24px;
    text-align: center;
  }
  .empty-icon { font-size: 3rem; opacity: 0.5; }

  .empty-sub {
    font-size: 0.75rem;
    color: var(--text-muted);
    max-width: 260px;
  }

  .status-bar {
    padding: 6px 14px;
    font-size: 0.72rem;
    color: var(--text-muted);
    background: var(--bg-secondary);
    border-top: 1px solid var(--border);
    line-height: 1.4;
    flex-shrink: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .status-bar.group-status {
    font-size: 0.68rem;
    padding: 5px 14px;
  }

  .status-bar.waiting { color: var(--warning); }
  .status-bar.offline { color: var(--danger); }

  @media (max-width: 768px) {
    .header-row { padding: 8px 12px; }
    .group-subbar { padding: 0 12px 8px; }
    .messages-container { padding: 12px; }
    .members-label { display: inline; }
    .world-pill-loc { max-width: 4.5em; }
  }
</style>
