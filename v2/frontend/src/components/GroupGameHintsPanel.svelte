<script>
  import { createEventDispatcher, onMount } from 'svelte'
  import {
    GROUP_CHAT_BASICS,
    GROUP_GAMES,
    REPLY_STYLES,
  } from '../lib/groupGameHints.js'

  export let groupId = ''
  export let expanded = false

  const dispatch = createEventDispatcher()

  let activeGameId = GROUP_GAMES[0]?.id || 'dice'
  const storageKey = () => `group_hints_expanded_${groupId || 'default'}`

  onMount(() => {
    try {
      const saved = localStorage.getItem(storageKey())
      if (saved !== null) expanded = saved === '1'
    } catch (_) {
      /* ignore */
    }
  })

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
</script>

<section class="hints-panel" class:expanded aria-label="群聊玩法提示">
  <button
    type="button"
    class="hints-toggle"
    on:click={toggleExpanded}
    aria-expanded={expanded}
  >
    <span class="toggle-icon">🎲</span>
    <span class="toggle-label">群聊玩法提示</span>
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
          </button>
        {/each}
      </div>

      {#if activeGame}
        <div class="game-detail" role="tabpanel">
          <p class="game-tagline">{activeGame.tagline}</p>

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
    max-height: min(42vh, 320px);
    overflow-y: auto;
    padding: 12px 16px 14px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    -webkit-overflow-scrolling: touch;
  }

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
