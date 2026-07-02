import { writable, derived } from 'svelte/store'
import { applyWorldClock, formatWorldTime, getWorldNowMs } from '../lib/timestamp.js'

export const worldTimeState = writable(null)

let tickTimer = null

export function syncWorldClock(payload) {
  applyWorldClock(payload)
  worldTimeState.set(payload)
  startWorldClockTick()
}

  function startWorldClockTick() {
  if (tickTimer) return
  tickTimer = setInterval(() => {
    worldTimeState.update(s => {
      if (!s) return s
      return { ...s, clock: formatWorldTime(getWorldNowMs()) }
    })
  }, 60000)
}

export const worldClockLabel = derived(worldTimeState, s => {
  if (!s) return ''
  return s.clock || formatWorldTime(getWorldNowMs())
})

export const worldLocationLabel = derived(worldTimeState, s => {
  if (!s) return '云栖里·许宅'
  return s.location || '云栖里·许宅'
})

export const worldClockHint = derived(worldTimeState, s => {
  if (!s) return ''
  const loc = s.location || '云栖里'
  return `${loc} · ${s.clock || formatWorldTime(getWorldNowMs())}`
})

export function stopWorldClockTick() {
  if (tickTimer) {
    clearInterval(tickTimer)
    tickTimer = null
  }
}
