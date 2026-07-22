<script>
  import { createEventDispatcher, onMount } from 'svelte'
  import {
    GROUP_CHAT_BASICS,
    GROUP_GAMES,
    REPLY_STYLES,
  } from '../lib/groupGameHints.js'
  import {
    applyGameAction,
    getCurrentGroupGame,
    startFateDice,
  } from '../lib/groupGames.js'

  export let groupId = ''
  export let expanded = false

  const dispatch = createEventDispatcher()

  let activeGameId = GROUP_GAMES[0]?.id || 'dice'
  let gameSession = null
  let gameLoading = false
  let gameBusy = false
  let gameError = ''
  let totalRounds = 3
  let loadedGroupId = ''
  const storageKey = () => `group_hints_expanded_${groupId || 'default'}`

  onMount(() => {
    try {
      const saved = localStorage.getItem(storageKey())
      if (saved !== null) expanded = saved === '1'
    } catch (_) {
      /* ignore */
    }
    loadCurrentGame()
  })

  async function loadCurrentGame() {
    if (!groupId) return
    const requestedGroup = groupId
    loadedGroupId = groupId
    gameLoading = true
    gameError = ''
    try {
      const session = await getCurrentGroupGame(groupId)
      if (groupId === requestedGroup) gameSession = session
    } catch (error) {
      if (groupId === requestedGroup) gameError = error.message || '加载游戏失败'
    } finally {
      if (groupId === requestedGroup) gameLoading = false
    }
  }

  async function startGame() {
    gameBusy = true
    gameError = ''
    try {
      gameSession = await startFateDice(groupId, Number(totalRounds))
    } catch (error) {
      gameError = error.message || '创建游戏失败'
      if (error.code === 'active_session_exists') await loadCurrentGame()
    } finally {
      gameBusy = false
    }
  }

  async function rollCurrent() {
    if (!gameSession?.current_turn) return
    gameBusy = true
    gameError = ''
    try {
      gameSession = await applyGameAction(
        gameSession,
        'roll',
        gameSession.current_turn.participant_ref_id,
      )
    } catch (error) {
      gameError = error.message || '掷骰失败'
      if (error.code === 'version_conflict') await loadCurrentGame()
    } finally {
      gameBusy = false
    }
  }

  async function endGame() {
    if (!gameSession) return
    gameBusy = true
    gameError = ''
    try {
      gameSession = await applyGameAction(gameSession, 'end', 'user')
    } catch (error) {
      gameError = error.message || '结束游戏失败'
    } finally {
      gameBusy = false
    }
  }

  function toggleExpanded() {
    expanded = !expanded
    try {
      localStorage.setItem(storageKey(), expanded ? '1' : '0')
    } catch (_) {
      /* ignore */
    }
  }

  function pickPrompt(text) {
    dispatch('select', text)
  }

  $: activeGame = GROUP_GAMES.find(g => g.id === activeGameId) || GROUP_GAMES[0]
  $: if (groupId && loadedGroupId && groupId !== loadedGroupId) loadCurrentGame()
  $: currentTurnName = gameSession?.current_turn?.display_name || ''
  $: totalConfiguredRounds = gameSession?.settings?.total_rounds || totalRounds
</script>

<section class="hints-panel" class:expanded aria-label="群聊玩法中心">
  <button
    type="button"
    class="hints-toggle"
    on:click={toggleExpanded}
    aria-expanded={expanded}
  >
    <span class="toggle-icon">🎲</span>
    <span class="toggle-label">群聊玩法中心</span>
    <span class="toggle-badge live">骰子已开放</span>
    <span class="toggle-meta">{expanded ? '收起' : '展开'}</span>
    <span class="caret">{expanded ? '▴' : '▾'}</span>
  </button>

  {#if expanded}
    <div class="hints-body">
      <div class="basics-block">
        <h4>{GROUP_CHAT_BASICS.title}</h4>
        <ul>
          {#each GROUP_CHAT_BASICS.items as item}
            <li>{item}</li>
          {/each}
        </ul>
      </div>

      <div class="game-tabs" role="tablist">
        {#each GROUP_GAMES as game (game.id)}
          <button
            type="button"
            role="tab"
            class="game-tab"
            class:active={activeGameId === game.id}
            aria-selected={activeGameId === game.id}
            on:click={() => activeGameId = game.id}
          >
            <span class="tab-icon">{game.icon}</span>
            <span class="tab-title">{game.title}</span>
            {#if !game.available}<span class="coming-dot" title="对话实验版">试</span>{/if}
          </button>
        {/each}
      </div>

      {#if activeGame}
        <div class="game-detail" role="tabpanel">
          <p class="game-tagline">{activeGame.tagline}</p>

          {#if activeGame.id === 'dice'}
            <div class="live-game-card">
              {#if gameLoading}
                <p class="game-state-note">正在同步本群游戏…</p>
              {:else if !gameSession || gameSession.status === 'cancelled'}
                <div class="start-row">
                  <label>
                    总轮数
                    <select bind:value={totalRounds} disabled={gameBusy}>
                      {#each [1, 2, 3, 5, 7, 10] as count}
                        <option value={count}>{count} 轮</option>
                      {/each}
                    </select>
                  </label>
                  <button type="button" class="primary-game-btn" on:click={startGame} disabled={gameBusy || !groupId}>
                    {gameBusy ? '创建中…' : '开始新一局'}
                  </button>
                </div>
              {:else}
                <div class="game-headline">
                  <div>
                    <strong>第 {gameSession.round_no} / {totalConfiguredRounds} 轮</strong>
                    <span>状态版本 v{gameSession.state_version}</span>
                  </div>
                  <span class:finished={gameSession.status === 'finished'} class="status-pill">
                    {gameSession.status === 'finished' ? '已结算' : '进行中'}
                  </span>
                </div>

                <div class="scoreboard">
                  {#each gameSession.participants as participant (participant.participant_ref_id)}
                    <div
                      class="score-row"
                      class:current={gameSession.current_turn?.participant_ref_id === participant.participant_ref_id}
                      class:winner={gameSession.winners?.includes(participant.participant_ref_id)}
                    >
                      <span class="seat">{participant.seat_no + 1}</span>
                      <span class="player-name">{participant.display_name}</span>
                      <span class="roll-value">
                        {gameSession.round_rolls?.[participant.participant_ref_id] ?? '—'}
                      </span>
                      <span class="score">{participant.score} 分</span>
                    </div>
                  {/each}
                </div>

                {#if gameSession.last_event?.text}
                  <p class="last-event">{gameSession.last_event.text}</p>
                {/if}

                {#if gameSession.status === 'running'}
                  <div class="action-row">
                    <button type="button" class="primary-game-btn" on:click={rollCurrent} disabled={gameBusy}>
                      {gameBusy ? '掷骰中…' : `让${currentTurnName}掷骰`}
                    </button>
                    <button type="button" class="secondary-game-btn" on:click={endGame} disabled={gameBusy}>结束本局</button>
                  </div>
                {:else}
                  <div class="action-row">
                    <button type="button" class="primary-game-btn" on:click={startGame} disabled={gameBusy}>再来一局</button>
                  </div>
                {/if}
              {/if}

              {#if gameError}
                <p class="game-error" role="alert">{gameError}</p>
              {/if}
            </div>
          {:else}
            <p class="experiment-note">该玩法仍是对话实验版：点击示例只会填入输入框，暂不计回合与分数。</p>
          {/if}

          <div class="detail-grid">
            <div class="detail-col">
              <h5>流程</h5>
              <ol>
                {#each activeGame.steps as step}
                  <li>{step}</li>
                {/each}
              </ol>
            </div>
            <div class="detail-col">
              <h5>规则</h5>
              <ul>
                {#each activeGame.rules as rule}
                  <li>{rule}</li>
                {/each}
              </ul>
            </div>
          </div>

          <div class="prompts-block">
            <h5>试试这样说 <span class="prompt-hint">（点击填入输入框）</span></h5>
            <div class="prompt-chips">
              {#each activeGame.prompts as prompt}
                <button type="button" class="prompt-chip" on:click={() => pickPrompt(prompt)}>
                  {prompt}
                </button>
              {/each}
            </div>
          </div>
        </div>
      {/if}

      <details class="styles-fold">
        <summary>{REPLY_STYLES.title}</summary>
        <div class="style-rows">
          {#each REPLY_STYLES.rows as row}
            <div class="style-row">
              <span class="style-role">{row.role}</span>
              <span class="style-hint">{row.hint}</span>
            </div>
          {/each}
        </div>
      </details>
    </div>
  {/if}
</section>

<style>
  .hints-panel {
    flex-shrink: 0;
    background: var(--bg-secondary);
    border-top: 1px solid var(--border);
  }

  .hints-toggle {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 14px;
    min-height: 44px;
    background: transparent;
    color: var(--text-secondary);
    font-size: 0.78rem;
    text-align: left;
    border: none;
    cursor: pointer;
    touch-action: manipulation;
    -webkit-tap-highlight-color: transparent;
    position: relative;
    z-index: 2;
  }

  .hints-toggle:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
  }

  .hints-panel.expanded .hints-toggle {
    border-bottom: 1px solid var(--border);
  }

  .toggle-icon { font-size: 1rem; }

  .toggle-label {
    font-weight: 600;
    color: var(--text-primary);
  }

  .toggle-badge {
    font-size: 0.68rem;
    font-weight: 600;
    color: var(--text-muted);
    padding: 2px 6px;
    border-radius: 4px;
    border: 1px solid var(--border);
    background: var(--bg-tertiary);
  }

  .toggle-badge.live {
    color: #69d59a;
    border-color: rgba(105, 213, 154, 0.35);
    background: rgba(105, 213, 154, 0.08);
  }

  .toggle-meta {
    color: var(--accent-light);
    font-size: 0.72rem;
    font-weight: 500;
    padding: 2px 8px;
    border-radius: 6px;
    background: rgba(124, 92, 252, 0.1);
  }

  .caret {
    margin-left: auto;
    color: var(--text-muted);
    font-size: 0.65rem;
  }

  .hints-body {
    max-height: min(55vh, 480px);
    overflow-y: auto;
    padding: 12px 16px 14px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    -webkit-overflow-scrolling: touch;
  }

  .experiment-note {
    margin: 0;
    font-size: 0.72rem;
    line-height: 1.45;
    color: var(--text-muted);
    padding: 8px 10px;
    border-left: 3px solid var(--border);
    background: var(--bg-tertiary);
  }

  .coming-dot {
    display: inline-grid;
    place-items: center;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    color: var(--text-muted);
    background: var(--bg-secondary);
    font-size: 0.58rem;
  }

  .live-game-card {
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 10px;
    margin-bottom: 10px;
    background: rgba(var(--accent-rgb, 99, 102, 241), 0.045);
  }

  .start-row,
  .action-row,
  .game-headline {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .start-row label {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--text-secondary);
    font-size: 0.74rem;
  }

  .start-row select {
    color: var(--text-primary);
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 5px 7px;
  }

  .primary-game-btn,
  .secondary-game-btn {
    border-radius: 7px;
    padding: 7px 11px;
    font-size: 0.74rem;
    font-weight: 600;
  }

  .primary-game-btn {
    color: white;
    border: 1px solid var(--accent);
    background: var(--accent);
  }

  .secondary-game-btn {
    color: var(--text-muted);
    border: 1px solid var(--border);
    background: transparent;
  }

  .primary-game-btn:disabled,
  .secondary-game-btn:disabled {
    opacity: 0.55;
    cursor: wait;
  }

  .game-headline strong {
    display: block;
    color: var(--text-primary);
    font-size: 0.78rem;
  }

  .game-headline div > span {
    color: var(--text-muted);
    font-size: 0.62rem;
  }

  .status-pill {
    padding: 2px 7px;
    border-radius: 999px;
    color: #69d59a;
    background: rgba(105, 213, 154, 0.1);
    font-size: 0.66rem;
  }

  .status-pill.finished {
    color: #f6c96b;
    background: rgba(246, 201, 107, 0.1);
  }

  .scoreboard {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin: 9px 0;
  }

  .score-row {
    display: grid;
    grid-template-columns: 20px minmax(70px, 1fr) 46px 42px;
    align-items: center;
    gap: 6px;
    min-height: 28px;
    padding: 3px 7px;
    border-radius: 6px;
    color: var(--text-secondary);
    background: var(--bg-tertiary);
    font-size: 0.72rem;
  }

  .score-row.current { outline: 1px solid var(--accent); }
  .score-row.winner { color: #f6c96b; }
  .seat { color: var(--text-muted); }
  .player-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .roll-value { color: var(--accent-light); font-weight: 700; text-align: center; }
  .score { text-align: right; }

  .last-event,
  .game-state-note,
  .game-error {
    margin: 7px 0;
    font-size: 0.7rem;
    line-height: 1.4;
  }

  .last-event { color: var(--text-secondary); }
  .game-state-note { color: var(--text-muted); }
  .game-error { color: #ff8e8e; }

  .basics-block h4,
  .game-detail h5,
  .detail-col h5 {
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--accent-light);
    margin-bottom: 6px;
    text-transform: none;
  }

  .basics-block ul,
  .detail-col ul,
  .detail-col ol {
    margin: 0;
    padding-left: 1.1rem;
    font-size: 0.74rem;
    color: var(--text-secondary);
    line-height: 1.45;
  }

  .basics-block li,
  .detail-col li {
    margin-bottom: 3px;
  }

  .game-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .game-tab {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 5px 10px;
    border-radius: 999px;
    background: var(--bg-tertiary);
    color: var(--text-secondary);
    font-size: 0.72rem;
    border: 1px solid transparent;
  }

  .game-tab.active {
    background: rgba(var(--accent-rgb, 99, 102, 241), 0.15);
    border-color: var(--accent);
    color: var(--accent-light);
  }

  .tab-icon { font-size: 0.85rem; }

  .game-tagline {
    font-size: 0.72rem;
    color: var(--text-muted);
    margin-bottom: 8px;
  }

  .detail-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 10px;
  }

  .prompts-block h5 {
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 8px;
  }

  .prompt-hint {
    font-weight: 400;
    color: var(--text-muted);
  }

  .prompt-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .prompt-chip {
    padding: 6px 10px;
    border-radius: var(--radius-sm);
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    color: var(--text-secondary);
    font-size: 0.72rem;
    line-height: 1.35;
    text-align: left;
    max-width: 100%;
  }

  .prompt-chip:hover {
    border-color: var(--accent);
    color: var(--accent-light);
    background: rgba(var(--accent-rgb, 99, 102, 241), 0.08);
  }

  .styles-fold {
    font-size: 0.74rem;
    color: var(--text-secondary);
    border-top: 1px dashed var(--border);
    padding-top: 8px;
  }

  .styles-fold summary {
    cursor: pointer;
    color: var(--text-muted);
    user-select: none;
  }

  .style-rows {
    margin-top: 8px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .style-row {
    display: flex;
    gap: 8px;
    font-size: 0.72rem;
  }

  .style-role {
    flex-shrink: 0;
    min-width: 4.5em;
    color: var(--accent-light);
    font-weight: 500;
  }

  .style-hint {
    color: var(--text-muted);
  }

  @media (max-width: 768px) {
    .detail-grid {
      grid-template-columns: 1fr;
    }

    .hints-body {
      max-height: 38vh;
      padding: 10px 12px 12px;
    }

    .game-tab .tab-title {
      max-width: 4.5em;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
</style>
