/** 统一为毫秒时间戳（后端 SQLite 存的是 Unix 秒） */
export function normalizeTimestamp(ts) {
  if (ts == null || ts === '') return getWorldNowMs()
  const n = Number(ts)
  if (!Number.isFinite(n) || n <= 0) return getWorldNowMs()
  return n < 1e12 ? Math.round(n * 1000) : Math.round(n)
}

export const DEFAULT_WORLD_TIMEZONE = 'Asia/Shanghai'

let worldTimezone = DEFAULT_WORLD_TIMEZONE
let serverAnchorMs = null
let syncedAtMs = null

/** 从后端同步世界时钟（health / WS init） */
export function applyWorldClock(payload) {
  if (!payload) return
  if (payload.timezone) worldTimezone = payload.timezone
  if (payload.timestamp != null) {
    serverAnchorMs = normalizeTimestamp(payload.timestamp)
    syncedAtMs = Date.now()
  }
}

export function getWorldTimezone() {
  return worldTimezone
}

/** 当前世界时间（毫秒），与后端同一时刻轴 */
export function getWorldNowMs() {
  if (serverAnchorMs == null || syncedAtMs == null) return Date.now()
  return serverAnchorMs + (Date.now() - syncedAtMs)
}

function getClockFormatter() {
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: worldTimezone,
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

/** 24 小时制 HH:mm，固定使用世界时区（云栖里） */
export function formatWorldTime(ts) {
  if (!ts) return ''
  return getClockFormatter().format(normalizeTimestamp(ts))
}

/** 聊天消息按时间排序，系统提示保持相对顺序并靠后 */
export function sortMessages(msgs) {
  return msgs
    .map((m, index) => ({ m, index }))
    .sort((a, b) => {
      if (a.m.type === 'system' && b.m.type !== 'system') return 1
      if (b.m.type === 'system' && a.m.type !== 'system') return -1
      if (a.m.type === 'system' && b.m.type === 'system') return a.index - b.index
      const ta = normalizeTimestamp(a.m.timestamp)
      const tb = normalizeTimestamp(b.m.timestamp)
      if (ta !== tb) return ta - tb
      return a.index - b.index
    })
    .map(({ m }) => m)
}

export function withNormalizedTimestamp(msg) {
  if (!msg || msg.type === 'system') return msg
  return { ...msg, timestamp: normalizeTimestamp(msg.timestamp) }
}
