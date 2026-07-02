<script>
  import { onMount } from 'svelte'
  import { loadDashboard, loadUserProfile, userProfile } from '../stores/characters.js'
  import { activeView, activeCharacterId, connect } from '../stores/chat.js'

  let dashboardData = null
  let loading = true

  onMount(async () => {
    await loadUserProfile()
    dashboardData = await loadDashboard()
    loading = false
  })

  function openPrivate(charId) {
    activeCharacterId.set(charId)
    activeView.set('private')
    connect('private', charId)
  }
</script>

<div class="dashboard">
  <div class="welcome">
    <h1>👋 {$userProfile.name}，欢迎回来</h1>
    <p>选择一个角色开始对话。手机端可点底部「详情」查看好感、情绪、记忆等完整数据。</p>
  </div>

  {#if loading}
    <div class="loading">加载中...</div>
  {:else if dashboardData}
    <div class="stats-grid">
      <div class="stat-card">
        <span class="stat-value">{dashboardData.total_characters || 0}</span>
        <span class="stat-label">角色总数</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{dashboardData.active_group_chats || 0}</span>
        <span class="stat-label">活跃群聊</span>
      </div>
    </div>

    {#if dashboardData.characters}
      <div class="char-preview">
        <h3>角色概览</h3>
        <div class="char-grid">
          {#each dashboardData.characters as char}
            <div class="char-card" on:click={() => openPrivate(char.id)} on:keydown={(e) => { if (e.key === 'Enter') openPrivate(char.id) }} role="button" tabindex="0">
              <div class="char-avatar-placeholder">{char.name?.[0] || '?'}</div>
              <div class="char-meta">
                <span class="char-name">{char.name}</span>
                <span class="char-stage">{char.stage_name}</span>
                <span class="char-mood">心情：{char.mood}</span>
                <span class="char-level">Lv.{char.level || 1} · 好感 {char.love}</span>
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/if}
  {/if}
</div>

<style>
  .dashboard {
    height: 100%;
    overflow-y: auto;
    padding: 32px;
  }

  .welcome h1 { font-size: 1.6rem; margin-bottom: 8px; }
  .welcome p { color: var(--text-secondary); margin-bottom: 32px; line-height: 1.5; }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
  }

  .stat-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .stat-value { font-size: 2rem; font-weight: 700; color: var(--accent-light); }
  .stat-label { font-size: 0.8rem; color: var(--text-muted); }

  .char-preview h3 {
    font-size: 1.1rem;
    margin-bottom: 16px;
    color: var(--text-secondary);
  }

  .char-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
  }

  .char-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    transition: border-color 0.2s;
    cursor: pointer;
  }
  .char-card:hover { border-color: var(--accent); }

  .char-avatar-placeholder {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--accent), var(--accent-blue));
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 700;
    font-size: 1rem;
    flex-shrink: 0;
  }

  .char-meta {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
  .char-name { font-weight: 600; font-size: 0.9rem; }
  .char-stage { font-size: 0.75rem; color: var(--text-muted); }
  .char-mood { font-size: 0.75rem; color: var(--text-secondary); }
  .char-level { font-size: 0.72rem; color: var(--accent-light); }

  .loading { color: var(--text-muted); padding: 32px; text-align: center; }

  @media (max-width: 768px) {
    .dashboard { padding: 16px; }
    .welcome h1 { font-size: 1.25rem; }
    .char-grid { grid-template-columns: 1fr; }
  }
</style>
