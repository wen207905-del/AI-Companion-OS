<script>
  import { onDestroy } from 'svelte'
  import { loadCharacterDetail } from '../stores/characters.js'
  import { lastPrivateMsgTimestamp, lastStatUpdate } from '../stores/chat.js'
  import CharacterAvatar from '../components/CharacterAvatar.svelte'
  import ProgressBar from '../components/ProgressBar.svelte'
  import { EMOTION_CN } from '../lib/labels.js'

  export let characterId

  let detail = null
  let loading = true
  let refreshTimer = null
  let lastLoadedId = null
  let fieldDeltas = {}
  let stageDelta = null
  let xpDelta = null
  let moodDelta = null
  let arousalDelta = null
  let arousalLabelDelta = null
  let deltaClearTimer = null
  let lastAppliedStatTs = 0

  const RELATION_FIELDS = [
    { key: 'love', label: '好感度', color: '#f87171' },
    { key: 'trust', label: '信任', color: '#38bdf8' },
    { key: 'attachment', label: '依恋', color: '#a78bfa' },
    { key: 'respect', label: '尊重', color: '#34d399' },
    { key: 'security', label: '安全感', color: '#fbbf24' },
    { key: 'possessiveness', label: '占有欲', color: '#fb923c' },
    { key: 'jealousy', label: '嫉妒', color: '#f472b6' },
    { key: 'intimacy_emotional', label: '情感亲密', color: '#818cf8' },
    { key: 'intimacy_physical', label: '身体亲密', color: '#c084fc' },
  ]

  const MOOD_EMOJI = {
    '开心': '😊', '高兴': '😊', '平静': '😌', '兴奋': '🤩',
    '疲惫': '😴', '压力': '😰', '孤独': '😔', '伤心': '😢',
    '生气': '😠', '不安': '😟', '害羞': '😳', '尴尬': '😅',
  }

  async function fetchDetail(id, showLoading = true) {
    if (showLoading) loading = true
    const d = await loadCharacterDetail(id)
    if (d && characterId === id) {
      detail = d
    }
    if (showLoading) loading = false
  }

  $: if (characterId && characterId !== lastLoadedId) {
    lastLoadedId = characterId
    fetchDetail(characterId, true)
  }

  $: if (characterId && $lastStatUpdate?.characterId === characterId
    && $lastStatUpdate.ts !== lastAppliedStatTs) {
    lastAppliedStatTs = $lastStatUpdate.ts
    const payload = $lastStatUpdate
    fieldDeltas = { ...(payload.deltas?.relationship || {}) }
    stageDelta = payload.deltas?.stage_name || null
    xpDelta = payload.deltas?.xp || null
    moodDelta = payload.deltas?.mood || null
    arousalDelta = payload.deltas?.arousal ?? null
    arousalLabelDelta = payload.deltas?.arousal_label || null

    if (payload.relationship) {
      detail = {
        ...(detail || { persona: {} }),
        relationship: payload.relationship,
        emotion: payload.emotion || detail?.emotion,
        growth: payload.growth || detail?.growth,
        arousal: payload.arousal || detail?.arousal,
      }
      loading = false
    }

    if (deltaClearTimer) clearTimeout(deltaClearTimer)
    deltaClearTimer = setTimeout(() => {
      fieldDeltas = {}
      stageDelta = null
      xpDelta = null
      moodDelta = null
      arousalDelta = null
      arousalLabelDelta = null
    }, 5000)
  }

  $: if (characterId && $lastPrivateMsgTimestamp > 0) {
    if (refreshTimer) clearTimeout(refreshTimer)
    refreshTimer = setTimeout(() => {
      fetchDetail(characterId, false)
    }, 400)
  }

  $: emotionEntries = detail?.emotion
    ? Object.entries(detail.emotion)
        .filter(([k, v]) => typeof v === 'number' && k !== 'character_id' && v >= 8)
        .map(([k, v]) => [EMOTION_CN[k] || k, v])
        .sort((a, b) => b[1] - a[1])
    : []

  onDestroy(() => {
    if (refreshTimer) clearTimeout(refreshTimer)
    if (deltaClearTimer) clearTimeout(deltaClearTimer)
  })
</script>

<div class="panel">
  {#if loading && !detail}
    <div class="loading">加载中…</div>
  {:else if detail}
    <div class="panel-header">
      <CharacterAvatar
        characterId={characterId}
        avatarUrl={detail.photo_template?.photo_url || ''}
        size={72}
        showStatus={true}
      />
      <div class="header-info">
        <h2 class="char-name">{detail.persona?.name || characterId}</h2>
        <span class="char-type-badge">{detail.persona?.type || '未知'}</span>
      </div>
    </div>

    {#if detail.relationship}
      <div class="section">
        <h3 class="section-title">关系阶段</h3>
        <div class="stage-display">
          <span class="stage-number">{detail.relationship.stage}</span>
          <div class="stage-meta">
            <span class="stage-name">
              {detail.relationship.stage_name}
              {#if stageDelta}
                <span class="stage-delta">→ {stageDelta}</span>
              {/if}
            </span>
            <span class="stage-love">好感 {detail.relationship.love}</span>
          </div>
        </div>
      </div>

      <div class="section">
        <h3 class="section-title">关系数值</h3>
        <div class="bars">
          {#each RELATION_FIELDS as field}
            <ProgressBar
              label={field.label}
              value={detail.relationship[field.key] || 0}
              max={100}
              color={field.color}
              delta={fieldDeltas[field.key]}
            />
          {/each}
        </div>
      </div>
    {/if}

    {#if detail.emotion}
      <div class="section">
        <h3 class="section-title">当前情绪</h3>
        <div class="mood-display">
          <span class="mood-emoji">{MOOD_EMOJI[detail.emotion.primary_mood] || '😐'}</span>
          <span class="mood-name">
            {detail.emotion.primary_mood}
            {#if moodDelta}
              <span class="mood-delta">→ {moodDelta}</span>
            {/if}
          </span>
        </div>
        {#if emotionEntries.length}
          <div class="emotion-bars">
            {#each emotionEntries as [label, val]}
              <ProgressBar label={label} value={val} max={100} color="#64748b" />
            {/each}
          </div>
        {/if}
      </div>
    {/if}

    {#if detail.arousal}
      <div class="section">
        <h3 class="section-title">发情度（当前情欲）</h3>
        <ProgressBar
          label={detail.arousal.label || '发情'}
          value={detail.arousal.level || 0}
          max={100}
          color="#e879f9"
          delta={arousalDelta}
        />
        <p class="arousal-meta">
          易感系数 {detail.arousal.susceptibility ?? '—'}
          · 基准 {detail.arousal.baseline ?? '—'}
          {#if arousalLabelDelta}
            <span class="arousal-label-delta"> → {arousalLabelDelta}</span>
          {/if}
        </p>
      </div>
    {/if}

    {#if detail.growth}
      <div class="section">
        <h3 class="section-title">成长等级</h3>
        <div class="growth-row">
          <span class="growth-level">Lv.{detail.growth.level || 1}</span>
          <span class="growth-xp">
            经验 {detail.growth.xp || 0}
            {#if xpDelta}
              <span class="xp-delta">+{xpDelta}</span>
            {/if}
          </span>
        </div>
        {#if detail.growth.milestones?.length}
          <div class="milestones">
            {#each detail.growth.milestones.slice(-3) as m}
              <span class="milestone-tag">{m}</span>
            {/each}
          </div>
        {/if}
      </div>
    {/if}

    {#if detail.album?.length}
      <div class="section">
        <h3 class="section-title">相册</h3>
        <div class="album-grid">
          {#each detail.album as item}
            <a class="album-thumb" href={item.url} target="_blank" rel="noopener">
              <img src={item.url} alt="角色照片" loading="lazy" />
            </a>
          {/each}
        </div>
      </div>
    {/if}

    {#if detail.recent_memories?.length}
      <div class="section">
        <h3 class="section-title">近期记忆</h3>
        <ul class="memory-list">
          {#each detail.recent_memories as mem}
            <li>{mem}</li>
          {/each}
        </ul>
      </div>
    {/if}

    {#if detail.body_experiences?.length}
      <div class="section">
        <h3 class="section-title">身体记忆</h3>
        <p class="section-desc">各部位与你的亲密经历</p>
        <div class="body-list">
          {#each detail.body_experiences as item}
            <div class="body-item">
              <div class="body-part">
                {item.part}
                {#if item.sensitivity != null}
                  <span class="sens-tag">敏感 {item.sensitivity}/10</span>
                {/if}
              </div>
              <p class="body-exp">{item.experience}</p>
            </div>
          {/each}
        </div>
      </div>
    {/if}

    {#if detail.persona?.intimate_state?.fetishes?.length}
      <div class="section">
        <h3 class="section-title">亲密偏好</h3>
        <div class="traits-cloud">
          {#each detail.persona.intimate_state.fetishes as item}
            <span class="trait-tag intimate">{item}</span>
          {/each}
        </div>
        {#if detail.persona.intimate_state.lewdness != null}
          <p class="intimate-meta">
            情欲指数 {detail.persona.intimate_state.lewdness}/100
            {#if detail.persona.intimate_state.desire}
              · 情感 {detail.persona.intimate_state.desire.emotional ?? '—'}
              · 身体 {detail.persona.intimate_state.desire.physical ?? '—'}
            {/if}
          </p>
        {/if}
      </div>
    {/if}

    {#if detail.persona?.core_tags?.length}
      <div class="section">
        <h3 class="section-title">性格特点</h3>
        <div class="traits-cloud">
          {#each detail.persona.core_tags as trait}
            <span class="trait-tag">{trait}</span>
          {/each}
        </div>
      </div>
    {/if}
  {:else}
    <div class="empty">选择角色查看详情</div>
  {/if}
</div>

<style>
  .panel {
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .panel-header {
    display: flex;
    align-items: center;
    gap: 16px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border);
  }

  .header-info { display: flex; flex-direction: column; gap: 4px; }
  .char-name { font-size: 1.2rem; font-weight: 700; }
  .char-type-badge {
    background: var(--bg-tertiary);
    color: var(--accent-light);
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 10px;
    align-self: flex-start;
  }

  .section { display: flex; flex-direction: column; gap: 10px; }
  .section-title {
    font-size: 0.82rem;
    color: var(--text-secondary);
    font-weight: 600;
  }
  .section-desc {
    font-size: 0.72rem;
    color: var(--text-muted);
    margin-top: -6px;
  }

  .stage-display {
    display: flex;
    align-items: center;
    gap: 12px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 12px 16px;
  }
  .stage-number {
    font-size: 1.8rem;
    font-weight: 800;
    color: var(--accent);
  }
  .stage-meta { display: flex; flex-direction: column; gap: 2px; }
  .stage-name { font-size: 1rem; color: var(--text-primary); }
  .stage-delta {
    font-size: 0.72rem;
    color: var(--success);
    margin-left: 4px;
  }
  .stage-love { font-size: 0.75rem; color: var(--text-muted); }

  .bars, .emotion-bars { display: flex; flex-direction: column; gap: 8px; }

  .mood-display {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .mood-emoji { font-size: 2rem; }
  .mood-name { font-size: 1rem; color: var(--text-primary); }
  .mood-delta {
    font-size: 0.75rem;
    color: var(--accent-light);
    margin-left: 4px;
  }

  .body-list { display: flex; flex-direction: column; gap: 10px; }
  .body-item {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 10px 12px;
  }
  .body-part {
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--accent-light);
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .sens-tag {
    font-size: 0.65rem;
    font-weight: 500;
    color: var(--text-muted);
    background: var(--bg-tertiary);
    padding: 1px 6px;
    border-radius: 8px;
  }
  .body-exp {
    font-size: 0.78rem;
    color: var(--text-secondary);
    line-height: 1.55;
  }

  .growth-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
  }
  .growth-level {
    font-size: 1.4rem;
    font-weight: 700;
    color: var(--accent-light);
  }
  .growth-xp { font-size: 0.85rem; color: var(--text-muted); }
  .xp-delta {
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--success);
    margin-left: 6px;
    padding: 1px 5px;
    border-radius: 6px;
    background: rgba(52, 211, 153, 0.15);
  }
  .milestones { display: flex; flex-wrap: wrap; gap: 6px; }
  .milestone-tag {
    font-size: 0.72rem;
    padding: 2px 8px;
    border-radius: 8px;
    background: var(--bg-tertiary);
    color: var(--text-secondary);
  }

  .memory-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .memory-list li {
    font-size: 0.78rem;
    color: var(--text-secondary);
    padding: 8px 10px;
    background: var(--bg-card);
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
  }

  .trait-tag.intimate {
    border-color: rgba(192, 132, 252, 0.35);
    color: #e9d5ff;
  }

  .intimate-meta {
    font-size: 0.72rem;
    color: var(--text-muted);
    margin-top: 4px;
  }

  .arousal-meta {
    margin-top: 6px;
    font-size: 0.75rem;
    color: var(--text-muted);
  }

  .arousal-label-delta {
    color: var(--accent-light);
  }

  .traits-cloud {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .trait-tag {
    background: var(--bg-tertiary);
    color: var(--text-secondary);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.8rem;
    border: 1px solid var(--border);
  }

  .album-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
  }

  .album-thumb {
    display: block;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid var(--border);
    aspect-ratio: 3 / 4;
  }

  .album-thumb img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .loading, .empty {
    color: var(--text-muted);
    text-align: center;
    padding: 32px 0;
  }
</style>
