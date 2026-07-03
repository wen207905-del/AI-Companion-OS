<script>
  import { createEventDispatcher } from 'svelte'

  const dispatch = createEventDispatcher()

  let inputValue = ''
  let textareaEl

  export let disabled = false
  export let compact = false
  export let showPhotoButton = false

  export function setDraft(text) {
    inputValue = text || ''
    if (textareaEl) {
      textareaEl.style.height = 'auto'
      textareaEl.style.height = Math.min(textareaEl.scrollHeight, 120) + 'px'
      textareaEl.focus()
    }
  }

  function handleSend() {
    const content = inputValue.trim()
    if (!content || disabled) return
    dispatch('send', content)
    inputValue = ''
  }

  function handleKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }
  function handlePhoto() {
    if (disabled) return
    dispatch('photo')
  }
</script>

<div class="chat-input-bar" class:compact>
  <div class="input-wrapper">
    {#if showPhotoButton}
      <button
        type="button"
        class="photo-btn"
        title="生成角色照片"
        aria-label="生成角色照片"
        disabled={disabled}
        on:click={handlePhoto}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="5" width="18" height="14" rx="2" />
          <circle cx="8.5" cy="10.5" r="1.5" />
          <path d="M21 16l-5.5-5.5L5 20" />
        </svg>
      </button>
    {/if}
    <textarea
      class="input-field"
      bind:value={inputValue}
      bind:this={textareaEl}
      placeholder="输入消息..."
      rows="1"
      disabled={disabled}
      on:keydown={handleKeydown}
      on:input={(e) => {
        // auto-grow
        const el = e.target
        el.style.height = 'auto'
        el.style.height = Math.min(el.scrollHeight, 120) + 'px'
      }}
    />
    <button class="send-btn" on:click={handleSend} disabled={!inputValue.trim() || disabled}>
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22 2L11 13" />
        <path d="M22 2L15 22L11 13L2 9L22 2Z" />
      </svg>
    </button>
  </div>
  <span class="hint">Enter 发送 · Shift+Enter 换行</span>
</div>

<style>
  .chat-input-bar {
    padding: 12px 20px 16px;
    background: var(--bg-secondary);
    border-top: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex-shrink: 0;
  }

  .input-wrapper {
    display: flex;
    gap: 8px;
    align-items: flex-end;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 8px 8px 8px 14px;
    transition: border-color 0.2s;
  }
  .input-wrapper:focus-within {
    border-color: var(--accent);
  }

  .input-field {
    flex: 1;
    background: transparent;
    color: var(--text-primary);
    font-size: 0.9rem;
    resize: none;
    max-height: 120px;
    line-height: 1.5;
  }
  .input-field::placeholder { color: var(--text-muted); }

  .photo-btn {
    width: 36px;
    height: 36px;
    border-radius: var(--radius-sm);
    background: rgba(124, 92, 252, 0.15);
    color: var(--accent-light);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .photo-btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .send-btn {
    width: 36px;
    height: 36px;
    border-radius: var(--radius-sm);
    background: var(--accent);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: opacity 0.2s, transform 0.15s;
  }
  .send-btn:hover:not(:disabled) {
    opacity: 0.9;
    transform: scale(1.05);
  }
  .send-btn:disabled {
    background: var(--bg-tertiary);
    color: var(--text-muted);
    cursor: not-allowed;
  }

  .hint {
    font-size: 0.7rem;
    color: var(--text-muted);
    text-align: right;
  }

  .chat-input-bar.compact {
    padding: 8px 12px 10px;
    gap: 0;
  }

  .chat-input-bar.compact .hint {
    display: none;
  }

  @media (max-width: 768px) {
    .chat-input-bar {
      padding: 8px 12px 10px;
    }

    .hint {
      display: none;
    }
  }
</style>
