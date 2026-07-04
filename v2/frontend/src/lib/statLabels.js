/** 关系数值中文标签 + 增量提示格式化 */

export const REL_LABEL_CN = {
  love: '好感',
  trust: '信任',
  attachment: '依恋',
  respect: '尊重',
  security: '安全感',
  possessiveness: '占有欲',
  jealousy: '嫉妒',
  intimacy_emotional: '情感亲密',
  intimacy_physical: '身体亲密',
}

export const AROUSAL_LABEL_CN = '发情度'

export const EMO_LABEL_CN = {
  happy: '开心',
  lonely: '孤独',
  miss_user: '想念',
  calm: '平静',
  excited: '兴奋',
  sad: '伤心',
  angry: '生气',
  tired: '疲惫',
}

/**
 * @param {object} deltas stat_update.deltas
 * @returns {{ label: string, delta: number }[]}
 */
export function formatStatDeltaChips(deltas = {}) {
  const chips = []
  const rel = deltas.relationship || {}
  for (const [key, val] of Object.entries(rel)) {
    if (typeof val === 'number' && Math.abs(val) >= 0.05) {
      chips.push({ label: REL_LABEL_CN[key] || key, delta: val })
    }
  }
  const emo = deltas.emotion || {}
  for (const [key, val] of Object.entries(emo)) {
    if (typeof val === 'number' && Math.abs(val) >= 0.05) {
      chips.push({ label: EMO_LABEL_CN[key] || key, delta: val })
    }
  }
  if (typeof deltas.xp === 'number' && deltas.xp > 0) {
    chips.push({ label: '经验', delta: deltas.xp })
  }
  if (typeof deltas.arousal === 'number' && Math.abs(deltas.arousal) >= 0.05) {
    chips.push({ label: AROUSAL_LABEL_CN, delta: deltas.arousal })
  }
  return chips.slice(0, 6)
}
