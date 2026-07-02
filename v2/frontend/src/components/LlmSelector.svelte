<script>
  import { onMount, onDestroy } from 'svelte'
  import {
    providers,
    currentLlm,
    llmLoading,
    loadProviders,
    setActiveLlmScope,
    setLlm,
    providerLabel,
    modelsForProvider,
  } from '../stores/llm.js'

  export let scopeType = 'private'   // 'private' | 'group'
  export let scopeId = ''

  let showPanel = false
  let rootEl

  onMount(() => {
    loadProviders()
    document.addEventListener('pointerdown', onDocPointerDown, true)
  })

  onDestroy(() => {
    document.removeEventListener('pointerdown', onDocPointerDown, true)
  })

  function onDocPointerDown(e) {
    if (!showPanel || !rootEl) return
    if (!rootEl.contains(e.target)) {
      showPanel = false
    }
  }

  $: if (scopeId) {
    setActiveLlmScope(scopeType, scopeId)
    showPanel = false
  }

  $: currentProvider = $providers.find(p => p.id === $currentLlm.provider)
  $: modelOptions = modelsForProvider($currentLlm.provider, $providers)
  $: isUnavailable = currentProvider && !currentProvider.available
  $: labelText = (() => {
    const name = providerLabel($currentLlm.provider, $providers)
    const model = $currentLlm.model
    if (model && model.length > 22) {
      return `${name} · ${model.slice(0, 20)}…`
    }
    return model ? `${name} · ${model}` : name
  })()

  function togglePanel(e) {
    e.stopPropagation()
    showPanel = !showPanel
  }

  async function selectProvider(providerId) {
    const p = $providers.find(x => x.id === providerId)
    if (!p || !p.available) return
    const model = p.default_model || p.models?.[0]?.id || ''
    await setLlm(scopeType, scopeId, providerId, model)
  }

  async function selectModel(modelId) {
    await setLlm(scopeType, scopeId, $currentLlm.provider, modelId)
  }
</script>

<div class="llm-selector" bind:this={rootEl}>
  <button
    class="llm-trigger"
    class:warn={isUnavailable}
    class:open={showPanel}
    on:click={togglePanel}
    title="切换 AI 模型"
    disabled={!scopeId || $llmLoading}
  >
    <span class="icon">🤖</span>
    <span class="label">{labelText}</span>
    <span class="caret">{showPanel ? '▴' : '▾'}</span>
  </button>

  {#if showPanel}
    <div class="panel">
      <div class="panel-title">选择 AI 引擎</div>
      <p class="panel-hint">每个私聊/群聊可独立切换，设置会自动保存</p>

      <div class="provider-list">
        {#each $providers as p (p.id)}
          <button
            class="provider-item"
            class:active={$currentLlm.provider === p.id}
            class:disabled={!p.available}
            on:click={() => selectProvider(p.id)}
            disabled={!p.available}
          >
            <span class="provider-name">{p.name}</span>
            {#if !p.available}
              <span class="badge off">未配置</span>
            {:else if $currentLlm.provider === p.id}
              <span class="badge on">使用中</span>
            {/if}
          </button>
        {/each}
      </div>

      {#if modelOptions.length > 1}
        <div class="model-section">
          <div class="model-label">模型</div>
          <select
            value={$currentLlm.model}
            on:change={e => selectModel(e.target.value)}
          >
            {#each modelOptions as m (m.id)}
              <option value={m.id}>{m.name}</option>
            {/each}
          </select>
        </div>
      {:else if $currentLlm.model}
        <div class="model-section">
          <div class="model-label">模型</div>
          <div class="model-single">{$currentLlm.model}</div>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .llm-selector {
    position: relative;
  }

  .llm-trigger {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text-secondary);
    font-size: 0.78rem;
    max-width: 280px;
  }

  .llm-trigger:hover:not(:disabled) {
    border-color: var(--accent);
    color: var(--text-primary);
  }

  .llm-trigger.warn {
    border-color: var(--warning);
    color: var(--warning);
  }

  .llm-trigger.open {
    border-color: var(--accent);
    color: var(--text-primary);
  }

  .llm-trigger:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .icon { font-size: 0.9rem; }
  .label {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .caret { font-size: 0.65rem; opacity: 0.7; }

  .panel {
    position: absolute;
    top: calc(100% + 8px);
    right: 0;
    z-index: 120;
    width: 280px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 14px;
  }

  .panel-title {
    font-weight: 600;
    font-size: 0.9rem;
    margin-bottom: 4px;
  }

  .panel-hint {
    font-size: 0.72rem;
    color: var(--text-muted);
    margin-bottom: 12px;
  }

  .provider-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .provider-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 12px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    font-size: 0.82rem;
    text-align: left;
  }

  .provider-item:hover:not(:disabled) {
    border-color: var(--accent);
  }

  .provider-item.active {
    border-color: var(--accent);
    background: rgba(124, 92, 252, 0.12);
  }

  .provider-item.disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .badge {
    font-size: 0.65rem;
    padding: 2px 6px;
    border-radius: 8px;
  }

  .badge.on {
    background: rgba(52, 211, 153, 0.15);
    color: var(--success);
  }

  .badge.off {
    background: rgba(248, 113, 113, 0.12);
    color: var(--danger);
  }

  .model-section {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
  }

  .model-label {
    font-size: 0.72rem;
    color: var(--text-muted);
    margin-bottom: 6px;
  }

  select {
    width: 100%;
    padding: 8px 10px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    font-size: 0.8rem;
  }

  .model-single {
    font-size: 0.78rem;
    color: var(--text-secondary);
    word-break: break-all;
  }

  @media (max-width: 768px) {
    .llm-trigger {
      max-width: 40px;
      min-width: 40px;
      min-height: 40px;
      padding: 0;
      justify-content: center;
    }

    .llm-trigger .label,
    .llm-trigger .caret {
      display: none;
    }

    .panel {
      width: min(280px, calc(100vw - 24px));
      right: -4px;
    }
  }
</style>
