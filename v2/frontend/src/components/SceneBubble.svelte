<script>
  export let message = {}

  import { characters } from '../stores/characters.js'
  import { formatWorldTime } from '../lib/timestamp.js'

  $: narration = message.narration || ''
  $: events = message.sceneEvents || message.events || []
  $: time = formatWorldTime(message.timestamp)

  function charName(id) {
    const found = $characters.find(c => c.id === id)
    return found?.name || id
  }
</script>

<div class="scene-message">
  <div class="scene-badge">叙述模式</div>
  {#if narration}
    <p class="scene-narration">{narration}</p>
  {/if}
  {#each events as ev (ev.character_id + (ev.action || '') + (ev.dialogue || ''))}
    <div class="scene-event">
      <span class="scene-char">{charName(ev.character_id)}</span>
      {#if ev.action}
        <span class="scene-action">*{ev.action}*</span>
      {/if}
      {#if ev.dialogue}
        <span class="scene-dialogue">「{ev.dialogue}」</span>
      {/if}
    </div>
  {/each}
  {#if !narration && !events.length && message.content}
    <p class="scene-narration">{message.content}</p>
  {/if}
  {#if message.parseFallback}
    <p class="scene-fallback">（场景解析降级为纯叙述）</p>
  {/if}
  <span class="scene-time">{time}</span>
</div>

<style>
  .scene-message {
    max-width: 92%;
    margin: 4px 0 12px;
    padding: 14px 16px;
    background: rgba(30, 41, 59, 0.55);
    border: 1px solid rgba(148, 163, 184, 0.25);
    border-left: 3px solid #64748b;
    border-radius: 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .scene-badge {
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #94a3b8;
  }

  .scene-narration {
    margin: 0;
    font-size: 0.88rem;
    line-height: 1.7;
    color: var(--text-secondary);
    font-style: italic;
  }

  .scene-event {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 8px 10px;
    background: rgba(15, 23, 42, 0.35);
    border-radius: 8px;
  }

  .scene-char {
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--accent-light);
  }

  .scene-action {
    font-size: 0.82rem;
    font-style: italic;
    color: #fbbf24;
  }

  .scene-dialogue {
    font-size: 0.88rem;
    line-height: 1.55;
    color: var(--text-primary);
  }

  .scene-fallback {
    margin: 0;
    font-size: 0.68rem;
    color: var(--text-muted);
  }

  .scene-time {
    font-size: 0.68rem;
    color: var(--text-muted);
    align-self: flex-end;
  }
</style>
