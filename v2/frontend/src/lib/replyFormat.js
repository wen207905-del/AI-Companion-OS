/**
 * Parse roleplay reply text into action / speech / narration segments.
 * Matches markers taught in the LLM prompt: *动作*, （动作）, 「对白」
 */

const MARKER_RE = /(\*[^*\n]+\*|「[^」\n]+」|（[^）\n]+）|"[^"\n]+"|“[^”\n]+”)/g

/**
 * @param {string} text
 * @returns {{ type: 'action' | 'speech' | 'narration', text: string }[]}
 */
export function parseReplyContent(text) {
  if (!text) return []

  const parts = String(text).split(MARKER_RE).filter(p => p.length > 0)
  return parts.map(part => classifySegment(part))
}

function classifySegment(part) {
  if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
    return { type: 'action', text: part.slice(1, -1) }
  }
  if (part.startsWith('「') && part.endsWith('」')) {
    return { type: 'speech', text: part.slice(1, -1) }
  }
  if (part.startsWith('（') && part.endsWith('）')) {
    return { type: 'action', text: part.slice(1, -1) }
  }
  if (
    (part.startsWith('"') && part.endsWith('"'))
    || (part.startsWith('“') && part.endsWith('”'))
  ) {
    return { type: 'speech', text: part.slice(1, -1) }
  }
  const trimmed = part.trim()
  if (!trimmed) {
    return { type: 'narration', text: part }
  }
  // 模型偶发省略号对白，仍按台词着色
  if (
    trimmed.startsWith('…') || trimmed.startsWith('...')
    || /^[哈啊嗯唔诶哼嘶呜呵]+/.test(trimmed)
    || (/[…\.]{2,}/.test(trimmed) && trimmed.length <= 80)
  ) {
    return { type: 'speech', text: trimmed }
  }
  return { type: 'narration', text: part }
}

/** Whether parsed content already contains explicit action markers. */
export function hasActionSegments(text) {
  return parseReplyContent(text).some(s => s.type === 'action')
}
