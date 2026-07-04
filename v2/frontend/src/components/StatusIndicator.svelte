<script>
  /**
   * StatusIndicator — 在线状态指示器，可选 mood 外环显示实时心情
   * Props:
   *   type: 'online' | 'typing' | 'offline'
   *   mood: 主导心情文案（可选）
   *   size: 像素 (默认 10)
   */
  export let type = 'offline'
  export let mood = ''
  export let size = 10

  const MOOD_RING = {
    '开心': '#34d399',
    '兴奋': '#fbbf24',
    '孤独': '#94a3b8',
    '想念': '#f472b6',
    '伤心': '#818cf8',
    '生气': '#f87171',
    '疲惫': '#a78bfa',
    '平静': '#38bdf8',
  }

  $: colorMap = {
    online: 'var(--success)',
    typing: 'var(--warning)',
    offline: 'var(--text-muted)',
  }

  $: color = colorMap[type] || colorMap.offline
  $: ringColor = MOOD_RING[mood] || ''
</script>

<span
  class="status-wrap"
  class:has-mood={!!ringColor}
  style="--size:{size}px; --ring:{ringColor};"
>
  <span
    class="status"
    class:pulse={type === 'typing'}
    style="width:{size}px; height:{size}px; background:{color};"
  />
</span>

<style>
  .status-wrap {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .status-wrap.has-mood {
    width: calc(var(--size) + 6px);
    height: calc(var(--size) + 6px);
    border-radius: 50%;
    box-shadow: 0 0 0 2px var(--ring);
  }
  .status {
    display: inline-block;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .status.pulse {
    animation: pulse 1.2s ease-in-out infinite;
  }
</style>
