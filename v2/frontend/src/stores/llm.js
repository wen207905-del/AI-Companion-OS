import { writable, get } from 'svelte/store'
import { apiUrl } from '../lib/api.js'

export const providers = writable([])
export const currentLlm = writable({ provider: 'deepseek', model: '' })
export const llmByScope = writable({})
export const activeLlmScope = writable('')
export const llmLoading = writable(false)

let wsRef = null

function scopeKey(scopeType, scopeId) {
  return `${scopeType}:${scopeId}`
}

export function bindWebSocket(ws) {
  wsRef = ws
}

export async function loadProviders() {
  try {
    const res = await fetch(apiUrl('/api/llm/providers'))
    if (!res.ok) return
    const data = await res.json()
    providers.set(data.providers || [])
    if (!get(currentLlm).model && data.default) {
      currentLlm.set({
        provider: data.default.provider || 'deepseek',
        model: data.default.model || '',
      })
    }
  } catch (e) {
    console.error('加载 LLM 提供商失败:', e)
  }
}

export function setActiveLlmScope(scopeType, scopeId) {
  if (!scopeType || !scopeId) return
  const key = scopeKey(scopeType, scopeId)
  activeLlmScope.set(key)
  const cached = get(llmByScope)[key]
  if (cached) {
    currentLlm.set(cached)
  } else {
    loadPref(scopeType, scopeId)
  }
}

export async function loadPref(scopeType, scopeId) {
  if (!scopeType || !scopeId) return
  const key = scopeKey(scopeType, scopeId)
  llmLoading.set(true)
  try {
    const res = await fetch(apiUrl(`/api/llm/pref/${scopeType}/${scopeId}`))
    if (!res.ok) return
    const data = await res.json()
    if (data.llm) {
      let provider = data.llm.provider
      let model = data.llm.model || ''
      if (provider === 'ollama') {
        provider = 'deepseek'
        model = model && model.includes('deepseek') ? model : 'deepseek-chat'
      }
      const llm = { provider, model }
      llmByScope.update(map => ({ ...map, [key]: llm }))
      if (get(activeLlmScope) === key) {
        currentLlm.set(llm)
      }
    }
  } catch (e) {
    console.error('加载 LLM 偏好失败:', e)
  } finally {
    llmLoading.set(false)
  }
}

export async function setLlm(scopeType, scopeId, provider, model) {
  const key = scopeKey(scopeType, scopeId)
  const llm = { provider, model: model || '' }
  currentLlm.set(llm)
  llmByScope.update(map => ({ ...map, [key]: llm }))

  const choice = { provider, model: model || null }
  try {
    await fetch(apiUrl(`/api/llm/pref/${scopeType}/${scopeId}`), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(choice),
    })
  } catch (e) {
    console.error('保存 LLM 偏好失败:', e)
  }

  if (wsRef && wsRef.readyState === WebSocket.OPEN) {
    wsRef.send(JSON.stringify({ type: 'set_llm', provider, model: model || null }))
  }
}

export function getCurrentLlmPayload() {
  const llm = get(currentLlm)
  return { provider: llm.provider, model: llm.model || undefined }
}

export function applyLlmFromInit(data, scopeType, scopeId) {
  if (!data?.llm?.provider) return
  let provider = data.llm.provider
  let model = data.llm.model || ''
  if (provider === 'ollama') {
    provider = 'deepseek'
    model = model && model.includes('deepseek') ? model : 'deepseek-chat'
  }
  const llm = { provider, model }
  if (scopeType && scopeId) {
    const key = scopeKey(scopeType, scopeId)
    llmByScope.update(map => ({ ...map, [key]: llm }))
    if (get(activeLlmScope) === key || !get(activeLlmScope)) {
      currentLlm.set(llm)
    }
  } else {
    currentLlm.set(llm)
  }
}

export function providerLabel(providerId, providerList) {
  const p = providerList.find(x => x.id === providerId)
  return p?.name || providerId
}

export function modelsForProvider(providerId, providerList) {
  const p = providerList.find(x => x.id === providerId)
  return p?.models || []
}
