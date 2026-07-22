import { apiUrl } from './api.js'

async function parseResponse(response) {
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = data?.detail
    const message = typeof detail === 'string'
      ? detail
      : detail?.message || data?.message || `请求失败（${response.status}）`
    const error = new Error(message)
    error.code = detail?.code || 'request_failed'
    error.status = response.status
    throw error
  }
  return data
}

function actionKey(action) {
  const random = globalThis.crypto?.randomUUID?.()
    || `${Date.now()}_${Math.random().toString(16).slice(2)}`
  return `${action}_${random}`
}

export async function getCurrentGroupGame(groupId) {
  const response = await fetch(apiUrl(`/api/v4/groups/${groupId}/game-sessions/current`), {
    cache: 'no-store',
  })
  const data = await parseResponse(response)
  return data.session || null
}

export async function startFateDice(groupId, totalRounds = 3) {
  const response = await fetch(apiUrl(`/api/v4/groups/${groupId}/game-sessions`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      game_type: 'fate_dice',
      settings: { total_rounds: totalRounds },
    }),
  })
  return parseResponse(response)
}

export async function applyGameAction(session, actionType, actorRefId = null) {
  const response = await fetch(apiUrl(`/api/v4/game-sessions/${session.id}/actions`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action_type: actionType,
      actor_ref_id: actorRefId,
      expected_version: session.state_version,
      idempotency_key: actionKey(actionType),
    }),
  })
  return parseResponse(response)
}
