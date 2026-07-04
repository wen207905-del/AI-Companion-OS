<script>
  export let job = {}

  $: status = job.status || 'queued'
  $: progressText = job.progress_text || defaultLabel(status)
  $: elapsed = job.elapsed_seconds || 0
  $: isActive = !['completed', 'failed'].includes(status)
  $: isFailed = status === 'failed'

  function defaultLabel(st) {
    const map = {
      queued: '排队中',
      generating: '生成中',
      uploading: '上传中',
      retrying: '换模型重试中',
      completed: '已完成',
      failed: '生成失败',
    }
    return map[st] || st
  }

  function statusClass(st) {
    if (st === 'failed') return 'failed'
    if (st === 'completed') return 'done'
    if (st === 'retrying') return 'retry'
    return 'active'
  }
</script>

{#if isActive || isFailed}
  <div class="job-progress" class:failed={isFailed}>
    <div class="job-header">
      <span class="job-icon">{isFailed ? '⚠' : '📷'}</span>
      <span class="job-title">{progressText}</span>
      {#if isActive && elapsed > 0}
        <span class="job-elapsed">{elapsed}s</span>
      {/if}
    </div>
    {#if isActive}
      <div class="bar-track">
        <div class="bar-fill status-{statusClass(status)}"></div>
      </div>
    {/if}
    {#if isFailed && job.error_message}
      <p class="job-error">{job.error_message}</p>
    {/if}
  </div>
{/if}

<style>
  .job-progress {
    margin: 8px 16px 4px 52px;
    padding: 10px 14px;
    border-radius: 12px;
    background: rgba(124, 92, 252, 0.1);
    border: 1px solid rgba(124, 92, 252, 0.25);
    animation: fadeIn 0.25s ease-out;
  }

  .job-progress.failed {
    background: rgba(239, 68, 68, 0.08);
    border-color: rgba(239, 68, 68, 0.3);
  }

  .job-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.82rem;
    color: var(--text-secondary);
  }

  .job-title {
    flex: 1;
    font-weight: 600;
    color: var(--text-primary);
  }

  .job-elapsed {
    font-size: 0.72rem;
    opacity: 0.7;
  }

  .bar-track {
    margin-top: 8px;
    height: 4px;
    border-radius: 2px;
    background: rgba(255, 255, 255, 0.08);
    overflow: hidden;
  }

  .bar-fill {
    height: 100%;
    width: 40%;
    border-radius: 2px;
    animation: shimmer 1.4s ease-in-out infinite;
  }

  .bar-fill.active {
    background: linear-gradient(90deg, var(--accent), var(--accent-light));
  }

  .bar-fill.retry {
    background: linear-gradient(90deg, #f59e0b, #fbbf24);
  }

  .job-error {
    margin: 6px 0 0;
    font-size: 0.75rem;
    color: #fca5a5;
    line-height: 1.4;
  }

  @keyframes shimmer {
    0% { transform: translateX(-100%); width: 30%; }
    50% { width: 55%; }
    100% { transform: translateX(250%); width: 30%; }
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
  }
</style>
