<script>
  /**
   * StatusIndicator — 在线状态指示器
   * Props:
   *   type: 'online' | 'typing' | 'offline'
   *   size: 像素 (默认 10)
   */
  export let type = 'offline'
  export let size = 10

  $: colorMap = {
    online: 'var(--success)',
    typing: 'var(--warning)',
    offline: 'var(--text-muted)',
  }

  $: color = colorMap[type] || colorMap.offline
</script>

<span
  class="status"
  class:pulse={type === 'typing'}
  style="width:{size}px; height:{size}px; background:{color};"
/>

<style>
  .status {
    display: inline-block;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .status.pulse {
    animation: pulse 1.2s ease-in-out infinite;
  }
</style>
