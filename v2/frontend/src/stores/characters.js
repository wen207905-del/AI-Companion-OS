import { writable, get } from 'svelte/store'
import { apiUrl } from '../lib/api.js'

export function avatarUrlFor(charId, list = get(characters)) {
  if (!charId) return ''
  return list.find(c => c.id === charId)?.avatar_url || ''
}

export const characters = writable([])
export const groups = writable([])
export const loading = writable(false)
export const userProfile = writable({ name: '许汉文', nickname: '汉文' })

const API_BASE = '/api'

async function apiError(res, fallback) {
  if (res.ok) return null
  let detail = fallback
  try {
    const data = await res.json()
    detail = data.detail || data.error || fallback
  } catch (_) { /* ignore */ }
  throw new Error(detail)
}

export async function loadUserProfile() {
  try {
    const res = await fetch(apiUrl('/api/user'))
    if (!res.ok) return
    const data = await res.json()
    userProfile.set({
      name: data.name || '许汉文',
      nickname: data.nickname || data.name || '汉文',
    })
  } catch (e) {
    console.error('加载用户档案失败:', e)
  }
}

export async function loadCharacters() {
  loading.set(true)
  try {
    const res = await fetch(apiUrl(`${API_BASE}/characters`))
    const data = await res.json()
    characters.set(data.characters || [])
  } catch (e) {
    console.error('加载角色列表失败:', e)
    characters.set([])
  } finally {
    loading.set(false)
  }
}

export async function loadCharacterDetail(charId) {
  try {
    const res = await fetch(apiUrl(`${API_BASE}/character/${charId}`))
    return await res.json()
  } catch (e) {
    console.error('加载角色详情失败:', e)
    return null
  }
}

/** 用 WS stat_update 增量刷新侧栏角色摘要 */
export function patchCharacterInList(charId, relationship, emotion, arousal) {
  if (!charId) return
  characters.update(list => list.map(c => {
    if (c.id !== charId) return c
    return {
      ...c,
      stage_name: relationship?.affection_grade ?? relationship?.stage_name ?? c.stage_name,
      love: relationship?.love ?? c.love,
      social_relation_label: relationship?.social_relation_label ?? c.social_relation_label,
      affection_grade: relationship?.affection_grade ?? c.affection_grade,
      affection_label: relationship?.affection_label ?? c.affection_label,
      current_activity: relationship?.current_activity ?? c.current_activity,
      mood: emotion?.primary_mood ?? c.mood,
      arousal: arousal?.level ?? c.arousal,
      arousal_label: arousal?.label ?? c.arousal_label,
    }
  }))
}

export async function loadDashboard() {
  try {
    const res = await fetch(apiUrl(`${API_BASE}/dashboard`))
    return await res.json()
  } catch (e) {
    console.error('加载仪表盘失败:', e)
    return null
  }
}

export async function loadGroups() {
  try {
    const res = await fetch(apiUrl(`${API_BASE}/groups?_=${Date.now()}`), {
      cache: 'no-store',
    })
    if (!res.ok) throw new Error('加载群聊列表失败')
    const data = await res.json()
    return data.groups || []
  } catch (e) {
    console.error('加载群聊列表失败:', e)
    return []
  }
}

/** 从服务端刷新群列表并写入 store */
export async function refreshGroups() {
  const list = await loadGroups()
  groups.set(list.filter(g => g.id !== 'default'))
  return get(groups)
}

/** WebSocket：远端新建群聊 */
export function applyGroupCreated(group) {
  if (!group?.id || group.id === 'default') return
  groups.update(list => {
    if (list.some(g => g.id === group.id)) {
      return list.map(g => g.id === group.id ? { ...g, ...group } : g)
    }
    return [...list, group]
  })
}

/** WebSocket：远端解散群聊 */
export function applyGroupDeleted(groupId) {
  if (!groupId || groupId === 'default') return
  groups.update(list => list.filter(g => g.id !== groupId))
}

export async function getGroup(groupId) {
  const res = await fetch(apiUrl(`${API_BASE}/group/${groupId}`))
  await apiError(res, '加载群聊失败')
  return await res.json()
}

export async function createGroup(name, memberIds) {
  const res = await fetch(apiUrl(`${API_BASE}/groups`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, member_ids: memberIds }),
  })
  await apiError(res, '创建群聊失败')
  return await res.json()
}

export async function addGroupMember(groupId, characterId) {
  const res = await fetch(apiUrl(`${API_BASE}/group/${groupId}/members`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ character_id: characterId }),
  })
  await apiError(res, '添加成员失败')
  return await res.json()
}

export async function removeGroupMember(groupId, characterId) {
  const res = await fetch(apiUrl(`${API_BASE}/group/${groupId}/members/${characterId}`), {
    method: 'DELETE',
  })
  await apiError(res, '移除成员失败')
  return await res.json()
}

export async function deleteGroup(groupId) {
  const res = await fetch(apiUrl(`${API_BASE}/group/${groupId}`), { method: 'DELETE' })
  await apiError(res, '删除群聊失败')
  const data = await res.json()
  groups.update(list => list.filter(g => g.id !== groupId))
  return data
}
