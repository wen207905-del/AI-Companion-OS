<script>
  /**
   * ProgressBar — 进度条组件
   * Props:
   *   label: 标签文字
   *   value: 当前值
   *   max: 最大值 (默认 100)
   *   color: 进度条颜色 (支持 CSS 色值)
   *   delta: 可选，本次变化量（正数显示绿色 +N，负数显示红色）
   */
  export let label = ''
  export let value = 0
  export let max = 100
  export let color = 'var(--accent)'
  export let delta = undefined

  $: pct = Math.min(100, Math.max(0, (value / max) * 100))
  $: displayVal = typeof value === 'number' ? value.toFixed(1) : value
  $: showDelta = typeof delta === 'number' && Math.abs(delta) >= 0.05
  $: deltaText = showDelta
    ? (delta > 0 ? `+${delta.toFixed(1)}` : delta.toFixed(1))
    : ''
</script>

<div class="progress-group">
  <div class="progress-label">
    <span class="label-text">{label}</span>
    <span class="label-value">
      {#if showDelta}
        <span class="delta" class:up={delta > 0} class:down={delta < 0}>{deltaText}</span>
      {/if}
      {displayVal}
    </span>
  </div>
  <div class="track">
    <div
      class="fill"
      style="width:{pct}%; background:{color};"
    />
  </div>
</div>

<style>
  .progress-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .progress-label {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
  }

  .label-text { color: var(--text-secondary); }
  .label-value {
    color: var(--text-muted);
    font-variant-numeric: tabular-nums;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .delta {
    font-size: 0.68rem;
    font-weight: 600;
    padding: 1px 5px;
    border-radius: 6px;
    animation: delta-pop 0.35s ease;
  }

  .delta.up {
    color: var(--success);
    background: rgba(52, 211, 153, 0.15);
  }

  .delta.down {
    color: var(--danger);
    background: rgba(248, 113, 113, 0.12);
  }

  @keyframes delta-pop {
    0% { transform: scale(0.85); opacity: 0; }
    100% { transform: scale(1); opacity: 1; }
  }

  .track {
    height: 5px;
    background: var(--bg-primary);
    border-radius: 3px;
    overflow: hidden;
  }

  .fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.6s ease;
  }
</style>
