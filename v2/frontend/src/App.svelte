<script>
  import { onMount, onDestroy } from 'svelte'
  import { writable } from 'svelte/store'
  import {
    characters,
    groups,
    loadCharacters,
    refreshGroups,
    loadUserProfile,
    getGroup,
    deleteGroup as deleteGroupApi,
  } from './stores/characters.js'
  import {
    activeView,
    activeCharacterId,
    activeGroupId,
    activeGroup,
    connect,
    disconnect,
    refreshActiveChat,
    connectionStatus,
  } from './stores/chat.js'
  import { apiUrl } from './lib/api.js'
  import { syncWorldClock } from './stores/worldTime.js'

  import CharacterAvatar from './components/CharacterAvatar.svelte'
  import StatusIndicator from './components/StatusIndicator.svelte'
  import CreateGroupModal from './components/CreateGroupModal.svelte'
  import Chat from './pages/Chat.svelte'
  import CharacterPanel from './pages/CharacterPanel.svelte'
  import MobileCharacterDetail from './pages/MobileCharacterDetail.svelte'
  import Dashboard from './pages/Dashboard.svelte'
  import ConfirmDialog from './components/ConfirmDialog.svelte'

  let showRightPanel = writable(true)
  let searchQuery = ''
  let sidebarCollapsed = false
  let showCreateModal = false
  let mobileTab = 'chat'
  let drawerOpen = false
  let isMobile = false
  let pendingDeleteGroupId = null
  let showDeleteGroupConfirm = false
  let appReady = false
  let lastGroupsSync = 0
  let backendOnline = true
  let backendCheckTimer = null
  let actionError = ''

  $: wsConnected = $connectionStatus === 'connected'
  $: filteredCharacters = $characters.filter(c =>
    !searchQuery || c.name?.toLowerCase().includes(searchQuery.toLowerCase())
  )
  $: displayGroups = $groups
  $: currentCharacter = $characters.find(c => c.id === $activeCharacterId)

  function checkMobile() {
    isMobile = window.innerWidth <= 768
    if (!isMobile) drawerOpen = false
  }

  onMount(async () => {
    checkMobile()
    window.addEventListener('resize', checkMobile)
    document.addEventListener('visibilitychange', onVisibilityChange)

    await loadUserProfile()
    await loadCharacters()
    await refreshGroups()

    const chars = $characters
    if (chars.length > 0) {
      await openPrivate(chars[0].id)
    } else if ($groups.length > 0) {
      await openGroup($groups[0].id)
    }
    appReady = true
    lastGroupsSync = Date.now()
    await checkBackend()
    backendCheckTimer = setInterval(checkBackend, 8000)
  })

  onDestroy(() => {
    window.removeEventListener('resize', checkMobile)
    document.removeEventListener('visibilitychange', onVisibilityChange)
    if (backendCheckTimer) clearInterval(backendCheckTimer)
  })

  async function checkBackend() {
    try {
      const res = await fetch(apiUrl('/api/health'), { cache: 'no-store' })
      backendOnline = res.ok
      if (res.ok) {
        const data = await res.json()
        if (data.world_time) syncWorldClock(data.world_time)
      }
    } catch {
      backendOnline = false
    }
  }

  async function onVisibilityChange() {
    if (!appReady || document.visibilityState !== 'visible') return
    const now = Date.now()
    if (now - lastGroupsSync < 3000) return
    lastGroupsSync = now
    await syncGroupsAfterRemoteChange()
    await loadCharacters()
    if ($activeView === 'private' && $activeCharacterId) {
      await refreshActiveChat()
    } else if ($activeView === 'group' && $activeGroupId) {
      await refreshActiveChat()
    }
  }

  async function syncGroupsAfterRemoteChange() {
    const list = await refreshGroups()
    if ($activeGroupId && !list.some(g => g.id === $activeGroupId)) {
      disconnect()
      activeGroupId.set(null)
      activeGroup.set(null)
      if (list.length > 0) {
        await openGroup(list[0].id)
      } else if ($characters.length > 0) {
        openPrivate($characters[0].id)
      }
    }
  }

  async function onGroupCreated(e) {
    const group = e.detail
    await refreshGroups()
    await openGroup(group.id)
  }

  async function onGroupDeleted(e) {
    const deletedId = e?.detail?.id
    if (deletedId && $activeGroupId === deletedId) {
      disconnect()
      activeGroupId.set(null)
      activeGroup.set(null)
    }
    lastGroupsSync = Date.now()
    const list = await refreshGroups()
    if (list.length > 0) {
      await openGroup(list[0].id)
    } else if ($characters.length > 0) {
      openPrivate($characters[0].id)
    } else {
      activeView.set('group')
    }
  }

  function requestDeleteGroup(groupId, e) {
    e?.stopPropagation?.()
    e?.preventDefault?.()
    pendingDeleteGroupId = groupId
    showDeleteGroupConfirm = true
  }

  async function confirmDeleteGroup() {
    const gid = pendingDeleteGroupId
    pendingDeleteGroupId = null
    showDeleteGroupConfirm = false
    if (!gid) return
    try {
      await deleteGroupApi(gid)
      lastGroupsSync = Date.now()
      actionError = ''
      await onGroupDeleted({ detail: { id: gid } })
    } catch (err) {
      actionError = err.message || '解散群聊失败'
      console.error(err)
    }
  }

  function cancelDeleteGroup() {
    pendingDeleteGroupId = null
    showDeleteGroupConfirm = false
  }

  async function openPrivate(charId) {
    drawerOpen = false
    actionError = ''
    activeCharacterId.set(charId)
    activeView.set('private')
    mobileTab = 'chat'
    connect('private', charId)
  }

  async function openGroup(groupId) {
    drawerOpen = false
    activeView.set('group')
    activeCharacterId.set(null)
    mobileTab = 'chat'
    actionError = ''
    try {
      const detail = await getGroup(groupId)
      if (!detail) {
        await refreshGroups()
        activeGroupId.set(null)
        activeGroup.set(null)
        if ($groups.length > 0 && $groups[0].id !== groupId) {
          await openGroup($groups[0].id)
        } else if ($characters.length > 0) {
          await openPrivate($characters[0].id)
        }
        return
      }
      activeGroup.set(detail)
      activeGroupId.set(groupId)
      connect('group', groupId)
    } catch (err) {
      actionError = err.message || '打开群聊失败'
      console.error(err)
    }
  }

  function openDrawer() {
    drawerOpen = true
  }

  function closeDrawer() {
    drawerOpen = false
  }

  function switchMobileTab(tab) {
    mobileTab = tab
    if (tab === 'chars') {
      drawerOpen = true
    } else if (tab === 'overview') {
      drawerOpen = false
      activeView.set('dashboard')
    } else if (tab === 'detail') {
      drawerOpen = false
    } else {
      drawerOpen = false
      if ($activeGroupId) {
        activeView.set('group')
      } else if ($activeCharacterId) {
        activeView.set('private')
      }
      refreshActiveChat()
    }
  }
</script>

<div class="app-layout">
  {#if !backendOnline}
    <div class="backend-banner" role="alert">
      后端未启动（:8000 连接被拒绝）。请另开终端运行：
      <code>cd D:\AI-Companion-OS\v2\backend; python main.py</code>
      或使用 <code>v2\start.ps1</code> 一键启动前后端。
    </div>
  {/if}
  {#if actionError}
    <div class="action-error" role="alert">{actionError}</div>
  {/if}
  {#if isMobile && drawerOpen}
    <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
    <div class="drawer-backdrop" on:click={closeDrawer}></div>
  {/if}

  <div class="app-body">
  <aside
    class="sidebar"
    class:collapsed={sidebarCollapsed && !isMobile}
    class:drawer={isMobile}
    class:drawer-open={isMobile && drawerOpen}
  >
    <div class="sidebar-header">
      <div class="logo">
        <span class="logo-icon">◆</span>
        <span class="logo-text" class:hidden={sidebarCollapsed && !isMobile}>Companion</span>
      </div>
      {#if isMobile}
        <button class="collapse-btn" on:click={closeDrawer}>×</button>
      {:else}
        <button class="collapse-btn" on:click={() => sidebarCollapsed = !sidebarCollapsed}>
          {sidebarCollapsed ? '›' : '‹'}
        </button>
      {/if}
    </div>

    {#if !sidebarCollapsed || isMobile}
      <div class="search-box">
        <input type="text" placeholder="搜索角色…" bind:value={searchQuery} />
      </div>

      <div class="section-label">私聊</div>
      <div class="char-list">
        {#each filteredCharacters as char (char.id)}
          <button
            class="char-item"
            class:active={$activeCharacterId === char.id && $activeView === 'private'}
            on:click={() => openPrivate(char.id)}
          >
            <CharacterAvatar characterId={char.id} avatarUrl={char.avatar_url} size={40} />
            <div class="char-info">
              <span class="char-name">{char.name}</span>
              <span class="char-stage">{char.stage_name}</span>
            </div>
            <StatusIndicator type={wsConnected ? 'online' : 'offline'} size={8} />
          </button>
        {/each}
      </div>

      <div class="sidebar-footer">
        <div class="footer-row">
          <span class="group-section-label">群聊</span>
          <button type="button" class="new-group-btn" on:click={() => showCreateModal = true}>+ 新建</button>
        </div>

        {#if displayGroups.length === 0}
          <p class="empty-groups">还没有群聊，点「新建」选人开聊</p>
        {/if}

        {#each displayGroups as g (g.id)}
          <div class="group-row" class:active={$activeView === 'group' && $activeGroupId === g.id}>
            <button
              type="button"
              class="group-btn group-item"
              class:active={$activeView === 'group' && $activeGroupId === g.id}
              on:click={() => openGroup(g.id)}
            >
              <span class="group-icon">👥</span>
              <span class="group-name">{g.name}</span>
              <span class="group-count">{g.member_count || 0}</span>
            </button>
            <button
              type="button"
              class="group-del-btn"
              title="解散群聊"
              aria-label="解散群聊"
              on:click={(e) => requestDeleteGroup(g.id, e)}
            >×</button>
          </div>
        {/each}
      </div>
    {/if}
  </aside>

  <main class="main-area">
    {#if isMobile && mobileTab === 'detail'}
      <MobileCharacterDetail initialId={$activeCharacterId} />
    {:else if $activeView === 'dashboard' || (isMobile && mobileTab === 'overview')}
      <Dashboard />
    {:else if $activeView === 'group' && $activeGroupId}
      <Chat
        view="group"
        groupId={$activeGroupId}
        onMenuClick={isMobile ? openDrawer : null}
        on:groupDeleted={onGroupDeleted}
      />
    {:else if $activeView === 'private' && $activeCharacterId}
      <Chat
        view="private"
        characterId={$activeCharacterId}
        onMenuClick={isMobile ? openDrawer : null}
      />
    {:else}
      <div class="no-chat">
        <div class="no-chat-icon">👥</div>
        <h2>创建你的第一个群聊</h2>
        <p>选择任意角色组合，不必所有人都在一个群里</p>
        <button type="button" class="cta-btn" on:click={() => showCreateModal = true}>新建群聊</button>
      </div>
    {/if}
  </main>

  {#if !isMobile && $showRightPanel && $activeCharacterId && $activeView === 'private'}
    <aside class="right-panel">
      <CharacterPanel characterId={$activeCharacterId} />
    </aside>
  {/if}
  </div>

  {#if isMobile}
    <nav class="mobile-nav">
      <button type="button" class:active={mobileTab === 'chars'} on:click={() => switchMobileTab('chars')}>
        <span class="nav-icon">👤</span>
        <span>角色</span>
      </button>
      <button type="button" class:active={mobileTab === 'chat'} on:click={() => switchMobileTab('chat')}>
        <span class="nav-icon">💬</span>
        <span>聊天</span>
      </button>
      <button type="button" class:active={mobileTab === 'detail'} on:click={() => switchMobileTab('detail')}>
        <span class="nav-icon">📋</span>
        <span>详情</span>
      </button>
      <button type="button" class:active={mobileTab === 'overview'} on:click={() => switchMobileTab('overview')}>
        <span class="nav-icon">📊</span>
        <span>总览</span>
      </button>
    </nav>
  {/if}
</div>

<CreateGroupModal
  characters={$characters}
  open={showCreateModal}
  on:created={onGroupCreated}
  on:close={() => showCreateModal = false}
/>

<ConfirmDialog
  open={showDeleteGroupConfirm}
  title="解散这个群聊？"
  message="群聊历史将被永久删除，所有设备上的列表都会同步更新。"
  confirmLabel="解散"
  on:confirm={confirmDeleteGroup}
  on:cancel={cancelDeleteGroup}
/>

<style>
  .app-layout {
    display: flex;
    height: 100vh;
    height: 100dvh;
    overflow: hidden;
    background: var(--bg-primary);
    flex-direction: column;
  }

  .backend-banner {
    flex-shrink: 0;
    padding: 10px 16px;
    background: rgba(248, 113, 113, 0.15);
    border-bottom: 1px solid var(--danger);
    color: #fecaca;
    font-size: 0.82rem;
    line-height: 1.5;
  }

  .backend-banner code {
    background: rgba(0, 0, 0, 0.25);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.78rem;
  }

  .action-error {
    flex-shrink: 0;
    padding: 8px 16px;
    background: rgba(248, 113, 113, 0.12);
    border-bottom: 1px solid var(--danger);
    color: #fecaca;
    font-size: 0.82rem;
  }

  .app-body {
    display: flex;
    flex: 1;
    min-height: 0;
    overflow: hidden;
    position: relative;
  }

  .drawer-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
    z-index: 90;
  }

  .sidebar {
    position: relative;
    width: 280px;
    min-width: 280px;
    background: var(--bg-secondary);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    transition: width 0.3s ease, min-width 0.3s ease, transform 0.3s ease;
    overflow: hidden;
    z-index: 100;
  }

  .sidebar.collapsed {
    width: 60px;
    min-width: 60px;
  }

  .sidebar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px;
    border-bottom: 1px solid var(--border);
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 700;
    font-size: 1.1rem;
    color: var(--accent-light);
  }

  .logo-text.hidden { display: none; }

  .collapse-btn {
    background: transparent;
    color: var(--text-muted);
    font-size: 1.2rem;
    padding: 4px 8px;
    border-radius: var(--radius-sm);
  }

  .search-box { padding: 12px 16px; }

  .search-box input {
    width: 100%;
    padding: 8px 12px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    font-size: 0.85rem;
  }

  .section-label {
    font-size: 0.7rem;
    color: var(--text-muted);
    padding: 4px 16px 6px;
  }

  .char-list {
    flex: 1;
    overflow-y: auto;
    padding: 0 8px;
    min-height: 120px;
  }

  .char-item {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    padding: 10px 12px;
    background: transparent;
    border-radius: var(--radius);
    color: var(--text-secondary);
    font-size: 0.9rem;
    text-align: left;
  }

  .char-item:hover { background: var(--bg-tertiary); }
  .char-item.active {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border-left: 3px solid var(--accent);
  }

  .char-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .char-name {
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .char-stage { font-size: 0.75rem; color: var(--text-muted); }

  .sidebar-footer {
    padding: 12px 16px;
    border-top: 1px solid var(--border);
  }

  .footer-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
  }

  .group-section-label {
    font-size: 0.7rem;
    color: var(--text-muted);
  }

  .new-group-btn {
    background: var(--accent);
    color: white;
    font-size: 0.72rem;
    padding: 4px 10px;
    border-radius: 10px;
    font-weight: 600;
  }

  .empty-groups {
    font-size: 0.78rem;
    color: var(--text-muted);
    padding: 8px 4px;
    line-height: 1.4;
  }

  .group-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 10px 12px;
    background: transparent;
    border-radius: var(--radius);
    color: var(--text-secondary);
    font-size: 0.9rem;
  }

  .group-btn:hover { background: var(--bg-tertiary); }
  .group-btn.active { background: var(--bg-tertiary); color: var(--accent-light); }

  .group-item { margin-bottom: 0; flex: 1; min-width: 0; }

  .group-row {
    display: flex;
    align-items: stretch;
    gap: 4px;
    margin-bottom: 4px;
    border-radius: var(--radius);
  }

  .group-row.active .group-btn {
    background: var(--bg-tertiary);
    color: var(--accent-light);
  }

  .group-del-btn {
    flex-shrink: 0;
    width: 32px;
    background: transparent;
    color: var(--text-muted);
    font-size: 1.1rem;
    border-radius: var(--radius-sm);
    opacity: 0.6;
  }

  .group-del-btn:hover {
    opacity: 1;
    color: var(--danger);
    background: rgba(248, 113, 113, 0.12);
  }

  .group-name {
    flex: 1;
    text-align: left;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .group-count {
    font-size: 0.7rem;
    color: var(--text-muted);
  }

  .main-area {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    background: var(--bg-primary);
  }

  .right-panel {
    width: 320px;
    min-width: 320px;
    background: var(--bg-secondary);
    border-left: 1px solid var(--border);
    overflow-y: auto;
  }

  .no-chat {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 32px;
    text-align: center;
    color: var(--text-secondary);
  }

  .no-chat-icon { font-size: 3.5rem; opacity: 0.5; }

  .no-chat h2 {
    color: var(--text-primary);
    font-size: 1.15rem;
  }

  .cta-btn {
    margin-top: 8px;
    padding: 12px 24px;
    background: var(--accent);
    color: white;
    border-radius: var(--radius);
    font-weight: 600;
    font-size: 0.95rem;
  }

  .mobile-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    background: var(--bg-secondary);
    border-top: 1px solid var(--border);
    padding: 6px 0 calc(6px + env(safe-area-inset-bottom, 0));
    z-index: 80;
  }

  .mobile-nav button {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 6px 2px;
    background: transparent;
    color: var(--text-muted);
    font-size: 0.62rem;
  }

  .mobile-nav button.active { color: var(--accent-light); }

  .nav-icon { font-size: 1.2rem; }

  @media (max-width: 768px) {
    .sidebar {
      position: fixed;
      top: 0;
      left: 0;
      bottom: 0;
      transform: translateX(-100%);
      min-width: 280px;
      width: 85vw;
      max-width: 320px;
    }

    .sidebar.drawer-open {
      transform: translateX(0);
    }

    .main-area {
      padding-bottom: calc(52px + env(safe-area-inset-bottom, 0));
    }

    .right-panel { display: none; }
  }
</style>
