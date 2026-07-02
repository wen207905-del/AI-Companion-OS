<script>
  export let characterId = ''
  export let size = 40
  export let showStatus = true

  $: initial = characterId?.[0]?.toUpperCase() || '?'

  // 根据 id 哈希生成稳定的渐变色
  $: hue = (characterId?.split('').reduce((a, c) => a + c.charCodeAt(0), 0) || 0) % 360
</script>

<div class="avatar-wrapper" style="width:{size}px; height:{size}px;">
  <div class="avatar-circle" style="--hue:{hue}; width:{size}px; height:{size}px;">
    <span class="avatar-text" style="font-size:{size * 0.4}px;">
      {initial}
    </span>
  </div>

  {#if showStatus}
    <span
      class="status-dot"
      style="width:{size * 0.22}px; height:{size * 0.22}px; border-width:{Math.max(2, size * 0.05)}px;"
    />
  {/if}
</div>

<style>
  .avatar-wrapper {
    position: relative;
    flex-shrink: 0;
  }

  .avatar-circle {
    border-radius: 50%;
    background: linear-gradient(135deg,
      hsl(var(--hue, 260), 60%, 45%),
      hsl(var(--hue, 260), 70%, 35%)
    );
    border: 2px solid transparent;
    background-clip: padding-box;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    /* 渐变边框光环 */
    box-shadow:
      0 0 0 2px var(--bg-secondary),
      0 0 0 4px hsl(var(--hue, 260), 60%, 50%, 0.4);
  }

  .avatar-text {
    color: white;
    font-weight: 700;
    user-select: none;
  }

  .status-dot {
    position: absolute;
    bottom: 0;
    right: 0;
    border-radius: 50%;
    background: var(--success);
    border-style: solid;
    border-color: var(--bg-primary);
  }
</style>
