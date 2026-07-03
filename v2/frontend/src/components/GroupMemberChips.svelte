<script>
  import CharacterAvatar from './CharacterAvatar.svelte'

  /** @type {{ id: string, name: string, love?: number, arousal?: number }[]} */
  export let members = []
</script>

<div class="chips-scroll" aria-label="群成员状态">
  {#each members as m (m.id)}
    <div class="chip">
      <CharacterAvatar characterId={m.id} avatarUrl={m.avatar_url} size={22} showStatus={false} />
      <span class="chip-name">{m.name}</span>
      {#if m.love != null}
        <span class="chip-stat love">{Math.round(m.love)}</span>
      {/if}
      {#if m.arousal != null}
        <span class="chip-stat arousal">{Math.round(m.arousal)}</span>
      {/if}
    </div>
  {/each}
</div>

<style>
  .chips-scroll {
    display: flex;
    gap: 8px;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    padding: 2px 0;
  }

  .chips-scroll::-webkit-scrollbar {
    display: none;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    flex-shrink: 0;
    padding: 4px 10px 4px 4px;
    border-radius: 999px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    font-size: 0.72rem;
    color: var(--text-secondary);
  }

  .chip-name {
    font-weight: 500;
    color: var(--text-primary);
    max-width: 4em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .chip-stat {
    font-variant-numeric: tabular-nums;
    font-size: 0.68rem;
    padding: 1px 5px;
    border-radius: 6px;
    font-weight: 600;
  }

  .chip-stat.love {
    background: rgba(124, 92, 252, 0.15);
    color: var(--accent-light);
  }

  .chip-stat.arousal {
    background: rgba(248, 113, 113, 0.12);
    color: #f87171;
  }
</style>
