<script>
  /** V4.1 右侧状态摘要：社会关系 + 好感等级 + 当前活动 + 实时心情 */
  export let relationship = null
  export let emotion = null

  $: primaryMood = emotion?.primary_mood || '平静'
  $: lonely = emotion?.lonely
  $: missUser = emotion?.miss_user
</script>

{#if relationship}
  <div class="status-panel">
    {#if relationship.social_relation_label}
      <div class="row">
        <span class="label">社会关系</span>
        <span class="value">{relationship.social_relation_label}</span>
      </div>
    {/if}
    {#if relationship.affection_label}
      <div class="row highlight">
        <span class="value">{relationship.affection_label}</span>
      </div>
    {:else if relationship.love != null}
      <div class="row highlight">
        <span class="value">好感 {relationship.love}</span>
      </div>
    {/if}
    {#if relationship.current_activity}
      <div class="row">
        <span class="label">当前活动</span>
        <span class="value">{relationship.current_activity}</span>
      </div>
    {/if}
    {#if primaryMood}
      <div class="row">
        <span class="label">当前心情</span>
        <span class="value mood-value">{primaryMood}</span>
      </div>
    {/if}
    {#if lonely != null || missUser != null}
      <div class="emotion-metrics">
        {#if lonely != null}
          <span class="metric" class:elevated={lonely >= 40}>孤独 {Math.round(lonely)}</span>
        {/if}
        {#if missUser != null}
          <span class="metric" class:elevated={missUser >= 40}>想念 {Math.round(missUser)}</span>
        {/if}
      </div>
    {/if}
  </div>
{/if}

<style>
  .status-panel {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px 14px;
    margin-bottom: 12px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
  }
  .row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 8px;
    font-size: 13px;
  }
  .row.highlight {
    justify-content: flex-start;
  }
  .row.highlight .value {
    color: #f9a8d4;
    font-weight: 600;
    font-size: 14px;
  }
  .label {
    color: rgba(255, 255, 255, 0.5);
    flex-shrink: 0;
  }
  .value {
    color: rgba(255, 255, 255, 0.92);
    text-align: right;
  }
  .mood-value {
    color: #c4b5fd;
    font-weight: 600;
  }
  .emotion-metrics {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding-top: 4px;
  }
  .metric {
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.06);
    color: rgba(255, 255, 255, 0.65);
  }
  .metric.elevated {
    background: rgba(251, 191, 36, 0.15);
    color: #fcd34d;
  }
</style>
