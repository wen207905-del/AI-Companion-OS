<script>
  import CharacterAvatar from './CharacterAvatar.svelte'

  export let characters = []
  export let selected = []
  export let min = 1
  export let max = 99

  function toggle(id) {
    if (selected.includes(id)) {
      if (selected.length > min) {
        selected = selected.filter(x => x !== id)
      }
    } else if (selected.length < max) {
      selected = [...selected, id]
    }
  }
</script>

<div class="picker">
  {#each characters as char (char.id)}
    <button
      type="button"
      class="pick-item"
      class:selected={selected.includes(char.id)}
      on:click={() => toggle(char.id)}
    >
      <CharacterAvatar characterId={char.id} size={36} showStatus={false} />
      <span class="pick-name">{char.name}</span>
      <span class="pick-check">{selected.includes(char.id) ? '✓' : ''}</span>
    </button>
  {/each}
</div>

<style>
  .picker {
    display: flex;
    flex-direction: column;
    gap: 4px;
    max-height: 320px;
    overflow-y: auto;
  }

  .pick-item {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 8px 10px;
    background: var(--bg-tertiary);
    border: 1px solid transparent;
    border-radius: var(--radius-sm);
    color: var(--text-secondary);
    text-align: left;
    transition: border-color 0.15s, background 0.15s;
  }

  .pick-item:hover { background: var(--bg-card); }
  .pick-item.selected {
    border-color: var(--accent);
    background: rgba(124, 92, 252, 0.12);
    color: var(--text-primary);
  }

  .pick-name { flex: 1; font-size: 0.9rem; }
  .pick-check {
    width: 20px;
    color: var(--accent-light);
    font-weight: 700;
  }
</style>
