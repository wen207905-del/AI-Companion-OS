/** 中文标签映射 */

export const EMOTION_CN = {
  happy: '开心',
  calm: '平静',
  stressed: '压力',
  tired: '疲惫',
  lonely: '孤独',
  excited: '兴奋',
  embarrassed: '尴尬',
  shy: '害羞',
  suspicious: '猜疑',
  sad: '伤心',
  angry: '生气',
  fearful: '不安',
}

export const CONNECTION_CN = {
  connected: '已连接',
  connecting: '连接中…',
  disconnected: '已断开',
}

export const PROVIDER_CN = {
  deepseek: 'DeepSeek 云端',
  qwen: 'Qwen 云端',
}

export function providerDisplayName(id, providers = []) {
  const p = providers.find(x => x.id === id)
  return p?.name || PROVIDER_CN[id] || id
}

/** 角色档案一行：姓名 · 职业 · 类型 · 年龄 */
export function formatCharacterProfileLine(persona) {
  if (!persona) return ''
  const parts = []
  if (persona.name) parts.push(persona.name)
  const base = persona.base_info || {}
  const job = base.occupation || base.identity
  if (job) parts.push(job)
  if (persona.type) parts.push(persona.type)
  if (base.age != null) parts.push(`${base.age}岁`)
  return parts.join(' · ')
}

/** 关系/情绪/发情度紧凑一行（状态栏用） */
export function formatCharacterStatsLine({ relationship, emotion, arousal } = {}) {
  const parts = []
  if (relationship?.stage_name) parts.push(relationship.stage_name)
  if (relationship?.love != null) parts.push(`好感 ${Math.round(relationship.love)}`)
  if (arousal?.level != null) {
    const label = arousal.label ? `·${arousal.label}` : ''
    parts.push(`发情 ${Math.round(arousal.level)}${label}`)
  } else if (typeof arousal === 'number') {
    parts.push(`发情 ${Math.round(arousal)}`)
  }
  if (relationship?.trust != null) parts.push(`信任 ${Math.round(relationship.trust)}`)
  if (emotion?.primary_mood) parts.push(emotion.primary_mood)
  return parts.join(' · ')
}

/** 群聊：每位成员 姓名·职业 */
export function formatGroupProfileLine(memberIds, characters = []) {
  if (!memberIds?.length) return ''
  const segments = memberIds.map(id => {
    const c = characters.find(x => x.id === id)
    if (!c) return id
    const job = c.occupation
    return job ? `${c.name}·${job}` : c.name
  })
  return `群内 ${segments.join(' / ')}`
}

/** 群聊：每位成员好感与发情度 */
export function formatGroupStatsLine(memberIds, characters = []) {
  if (!memberIds?.length) return ''
  const segments = memberIds.map(id => {
    const c = characters.find(x => x.id === id)
    if (!c) return null
    const love = c.love != null ? Math.round(c.love) : '—'
    const ar = c.arousal != null ? Math.round(c.arousal) : null
    return ar != null ? `${c.name}${love}♨${ar}` : `${c.name}${love}`
  }).filter(Boolean)
  return segments.length ? `好感/发情 ${segments.join(' / ')}` : ''
}

/** 聊天状态栏：关系、情绪、情欲、性癖等紧凑摘要（详情面板等仍可用） */
export function formatCharacterIntimateStatus({ relationship, emotion, intimate, persona } = {}) {
  const profile = formatCharacterProfileLine(persona)
  const stats = formatCharacterStatsLine({ relationship, emotion })
  const extra = []

  if (relationship?.intimacy_emotional != null) {
    extra.push(`情感亲密 ${Math.round(relationship.intimacy_emotional)}`)
  }
  if (relationship?.intimacy_physical != null) {
    extra.push(`身体亲密 ${Math.round(relationship.intimacy_physical)}`)
  }

  const desire = intimate?.desire || {}
  if (desire.emotional != null) {
    extra.push(`情感 ${Math.round(desire.emotional)}`)
  }
  if (desire.physical != null) {
    extra.push(`身体 ${Math.round(desire.physical)}`)
  }
  if (intimate?.lewdness != null) {
    extra.push(`情欲 ${intimate.lewdness}`)
  }

  const fetishes = intimate?.fetishes || []
  if (fetishes.length) {
    const sample = fetishes.slice(0, 2).join('、')
    extra.push(`性癖 ${sample}${fetishes.length > 2 ? '…' : ''}`)
  }

  const sensitivity = intimate?.sensitivity || {}
  const sensTop = Object.entries(sensitivity)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 2)
    .map(([k, v]) => `${SENSITIVITY_CN[k] || k}${v}`)
  if (sensTop.length) {
    extra.push(`敏感 ${sensTop.join('、')}`)
  }

  const lines = []
  if (profile) lines.push(profile)
  const statLine = [stats, ...extra].filter(Boolean).join(' · ')
  if (statLine) lines.push(statLine)
  return lines.join('\n')
}

export const SENSITIVITY_CN = {
  neck: '颈',
  ears: '耳',
  chest: '胸',
  breast: '胸',
  waist: '腰',
  thighs: '腿',
  inner_thigh: '腿内侧',
  lips: '唇',
  spine: '背',
  hands: '手',
  hips: '臀',
  belly: '腹',
  shoulders: '肩',
}

export function formatStatusLine({
  connection,
  waiting,
  streaming,
  llm,
  providers,
  typingNames = [],
  profileHint = '',
  statsHint = '',
  characterHint = '',
}) {
  const conn = CONNECTION_CN[connection] || connection
  const model = llm?.model ? ` · ${llm.model}` : ''
  const ai = llm?.provider
    ? providerDisplayName(llm.provider, providers) + model
    : '未选择模型'
  let wait = ''
  if (streaming) {
    wait = ' · 正在输出…'
  } else if (waiting) {
    wait = typingNames.length
      ? ` · ${typingNames.join('、')} 正在输入…`
      : ' · 等待回复…'
  }
  const tech = `${conn} · ${ai}${wait}`

  const lines = []
  if (profileHint) lines.push(profileHint)
  if (statsHint) lines.push(statsHint)
  if (!profileHint && !statsHint && characterHint) lines.push(characterHint)
  lines.push(tech)
  return lines.join('\n')
}
