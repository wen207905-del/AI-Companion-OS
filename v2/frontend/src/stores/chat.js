import { writable, derived, get } from 'svelte/store'
import { characters, patchCharacterInList, applyGroupCreated, applyGroupDeleted, getGroup, groups } from './characters.js'
import { bindWebSocket, applyLlmFromInit, getCurrentLlmPayload, setActiveLlmScope } from './llm.js'
import { apiUrl, wsUrl } from '../lib/api.js'
import { normalizeTimestamp, sortMessages, withNormalizedTimestamp, getWorldNowMs } from '../lib/timestamp.js'
import { syncWorldClock } from './worldTime.js'

export const activeView = writable('private')
export const activeCharacterId = writable(null)
export const activeGroupId = writable(null)
export const activeGroup = writable(null)
export const messages = writable([])
export const isConnecting = writable(false)
export const connectionStatus = writable('disconnected')
export const isWaitingReply = writable(false)
export const isLoadingHistory = writable(false)
export const lastPrivateMsgTimestamp = writable(0)
export const lastStatUpdate = writable(null)
export const typingCharacters = writable([])
export const isStreamingReply = writable(false)
export const chatMode = writable('chat')
export const dmListVersion = writable(0)
export const imageJobs = writable({})

let ws = null
let reconnectTimer = null
let currentView = 'private'
let currentId = null
let historyLoadedFor = null
let intentionalClose = false
let connectSeq = 0
let reconnectFailures = 0

function canApplyHistory(scopeSeq, view, id) {
  return connectSeq === scopeSeq && currentView === view && currentId === id
}

function setSortedMessages(list) {
  messages.set(sortMessages(list.map(m => withNormalizedTimestamp(m))))
}

function updateSortedMessages(updater) {
  messages.update(msgs => sortMessages(updater(msgs).map(m => withNormalizedTimestamp(m))))
}

function teardownSocket(socket) {
  if (!socket) return
  socket.onopen = null
  socket.onmessage = null
  socket.onclose = null
  socket.onerror = null
  if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
    socket.close()
  }
}

function parseStoredAction(raw) {
  if (!raw) return null
  if (typeof raw === 'object') return raw
  try {
    return JSON.parse(raw)
  } catch {
    return raw
  }
}

function mapPrivateHistoryMessage(m, characterId) {
  const contentType = m.content_type || 'text'
  if (contentType === 'scene') {
    const sceneData = parseStoredAction(m.action)
    return {
      id: m.id,
      type: 'scene',
      senderType: m.sender_type,
      senderId: m.sender_type === 'character' ? characterId : 'user',
      content: m.content,
      contentType: 'scene',
      narration: sceneData?.narration || '',
      sceneEvents: sceneData?.events || [],
      participants: sceneData?.participants || [],
      parseFallback: !!sceneData?.parse_fallback,
      timestamp: normalizeTimestamp(m.timestamp),
      edited: !!m.edited,
    }
  }
  return {
    id: m.id,
    type: 'chat',
    senderType: m.sender_type,
    senderId: m.sender_type,
    content: m.content,
    contentType,
    action: parseStoredAction(m.action),
    innerThought: m.inner_thought || '',
    timestamp: normalizeTimestamp(m.timestamp),
    edited: !!m.edited,
  }
}

async function loadPrivateHistory(characterId, { replace = true, scopeSeq, view = 'private' } = {}) {
  try {
    const res = await fetch(apiUrl(`/api/chat/${characterId}/history?limit=50`))
    if (!res.ok) return
    if (scopeSeq != null && !canApplyHistory(scopeSeq, view, characterId)) return
    const data = await res.json()
    const hist = (data.messages || []).map(m => mapPrivateHistoryMessage(m, characterId))
    if (replace || hist.length) {
      setSortedMessages(hist)
    }
    if (scopeSeq == null || canApplyHistory(scopeSeq, view, characterId)) {
      historyLoadedFor = characterId
    }
  } catch (e) {
    console.error('加载私聊历史失败:', e)
  }
}

async function loadGroupHistory(groupId, { replace = true, scopeSeq, view = 'group' } = {}) {
  try {
    const res = await fetch(apiUrl(`/api/group/${groupId}/history?limit=100`))
    if (!res.ok) return
    if (scopeSeq != null && !canApplyHistory(scopeSeq, view, groupId)) return
    const data = await res.json()
    const charList = get(characters)
    const hist = (data.messages || []).map(m => {
      let charName = ''
      if (m.sender_type === 'character') {
        const found = charList.find(c => c.id === m.sender_id)
        charName = found?.name || m.sender_id
      }
      return {
        id: m.id,
        type: 'chat',
        senderType: m.sender_type,
        senderId: m.sender_id,
        characterName: charName,
        content: m.content,
        innerThought: m.inner_thought || '',
        timestamp: normalizeTimestamp(m.timestamp),
        edited: !!m.edited,
      }
    })
    if (replace || hist.length) {
      setSortedMessages(hist)
    }
    if (scopeSeq == null || canApplyHistory(scopeSeq, view, groupId)) {
      historyLoadedFor = groupId
    }
  } catch (e) {
    console.error('加载群聊历史失败:', e)
  }
}

function upsertMessage(id, patch) {
  updateSortedMessages(msgs => {
    const idx = msgs.findIndex(m => m.id === id)
    const merged = withNormalizedTimestamp({ id, type: 'chat', ...patch })
    if (idx >= 0) {
      const next = [...msgs]
      next[idx] = { ...next[idx], ...merged }
      return next
    }
    return [...msgs, merged]
  })
}

function appendStreamDelta(id, delta) {
  messages.update(msgs => msgs.map(m =>
    m.id === id ? { ...m, content: (m.content || '') + delta } : m
  ))
}

async function handleRemoteGroupDeleted(groupId) {
  applyGroupDeleted(groupId)
  if (get(activeView) !== 'group' || get(activeGroupId) !== groupId) {
    return
  }

  disconnect()
  activeGroupId.set(null)
  activeGroup.set(null)

  const list = get(groups)
  if (list.length > 0) {
    try {
      const detail = await getGroup(list[0].id)
      activeGroup.set(detail)
      activeGroupId.set(list[0].id)
      activeView.set('group')
      await connect('group', list[0].id)
    } catch (e) {
      console.error('切换群聊失败:', e)
      messages.set([{
        type: 'system',
        content: '该群聊已在其他设备上解散',
      }])
    }
    return
  }

  const chars = get(characters)
  if (chars.length > 0) {
    activeCharacterId.set(chars[0].id)
    activeView.set('private')
    await connect('private', chars[0].id)
  } else {
    activeView.set('private')
    messages.set([{
      type: 'system',
      content: '该群聊已在其他设备上解散',
    }])
  }
}

function handleMessage(data, view) {
  if (data.type === 'user_message_saved') {
    let isNewRemote = false
    updateSortedMessages(msgs => {
      if (data.client_id) {
        const idx = msgs.findIndex(m => m.id === data.client_id)
        if (idx >= 0) {
          const next = [...msgs]
          next[idx] = {
            ...next[idx],
            id: data.id,
            content: data.content ?? next[idx].content,
            timestamp: normalizeTimestamp(data.timestamp ?? next[idx].timestamp),
          }
          return next
        }
      }
      if (msgs.some(m => m.id === data.id)) return msgs
      isNewRemote = true
      return [...msgs, {
        id: data.id,
        type: 'chat',
        senderType: 'user',
        senderId: 'user',
        content: data.content,
        timestamp: normalizeTimestamp(data.timestamp),
      }]
    })
    if (isNewRemote || data.client_id) {
      isWaitingReply.set(true)
    }
    return
  }

  if (data.type === 'mode_updated') {
    if (data.mode === 'chat' || data.mode === 'scene') {
      chatMode.set(data.mode)
    }
    return
  }

  if (data.type === 'scene_event') {
    isWaitingReply.set(false)
    isStreamingReply.set(false)
    typingCharacters.set([])
    updateSortedMessages(msgs => [...msgs, withNormalizedTimestamp({
      id: data.id,
      type: 'scene',
      senderType: 'character',
      senderId: data.character_id || '',
      content: data.content || '',
      contentType: 'scene',
      narration: data.narration || '',
      sceneEvents: data.events || [],
      participants: data.participants || [],
      parseFallback: !!data.parse_fallback,
      timestamp: data.timestamp,
    })])
    if (view === 'private') {
      lastPrivateMsgTimestamp.set(Date.now())
    }
    return
  }

  if (data.type === 'init') {
    if (data.world_time) {
      syncWorldClock(data.world_time)
    }
    if (data.mode === 'chat' || data.mode === 'scene') {
      chatMode.set(data.mode)
    }
    if (data.character?.id) {
      applyLlmFromInit(data, 'private', data.character.id)
      if (historyLoadedFor !== data.character.id) {
        loadPrivateHistory(data.character.id, {
          scopeSeq: connectSeq,
          view: 'private',
          id: data.character.id,
        })
      }
    } else if (data.group?.id) {
      applyLlmFromInit(data, 'group', data.group.id)
      activeGroup.set(data.group)
      activeGroupId.set(data.group.id)
      if (historyLoadedFor !== data.group.id) {
        loadGroupHistory(data.group.id, {
          scopeSeq: connectSeq,
          view: 'group',
          id: data.group.id,
        })
      }
    } else {
      applyLlmFromInit(data)
      messages.set([{ type: 'system', content: '已加入群聊' }])
    }
    isLoadingHistory.set(false)
    return
  }

  if (data.type === 'llm_updated') {
    const scope = view === 'private' ? 'private' : 'group'
    const scopeId = view === 'private' ? get(activeCharacterId) : get(activeGroupId)
    applyLlmFromInit(data, scope, scopeId)
    return
  }

  if (data.type === 'stat_update') {
    lastStatUpdate.set({
      characterId: data.character_id,
      relationship: data.relationship,
      emotion: data.emotion,
      growth: data.growth,
      arousal: data.arousal,
      deltas: data.deltas || {},
      ts: Date.now(),
    })
    patchCharacterInList(data.character_id, data.relationship, data.emotion, data.arousal)
    lastPrivateMsgTimestamp.set(Date.now())
    return
  }

  if (data.type === 'emotion_update') {
    lastStatUpdate.set({
      characterId: data.character_id,
      relationship: null,
      emotion: data.emotion,
      growth: null,
      arousal: null,
      deltas: data.deltas || { emotion: data.emotion_delta || {} },
      ts: Date.now(),
    })
    patchCharacterInList(data.character_id, null, data.emotion, null)
    return
  }

  if (data.type === 'character_dm_created') {
    dmListVersion.update(v => v + 1)
    return
  }

  if (data.type === 'group_created') {
    if (data.group) {
      applyGroupCreated(data.group)
    }
    return
  }

  if (data.type === 'group_deleted') {
    const gid = data.group_id
    if (gid) {
      handleRemoteGroupDeleted(gid)
    }
    return
  }

  if (data.type === 'regenerate_start') {
    const mid = data.message_id
    if (!mid) return
    isWaitingReply.set(true)
    isStreamingReply.set(true)
    messages.update(msgs => msgs.map(m =>
      m.id === mid
        ? {
            ...m,
            content: '',
            innerThought: '',
            isStreaming: true,
          }
        : m
    ))
    return
  }

  if (data.type === 'stream_start') {
    if (view === 'private') {
      isWaitingReply.set(false)
    }
    if (data.character_id || data.sender_id) {
      const cid = data.character_id || data.sender_id
      typingCharacters.update(list => list.filter(c => c.id !== cid))
    }
    isStreamingReply.set(true)
    upsertMessage(data.id, {
      senderType: data.sender_type || 'character',
      senderId: data.sender_id || data.character_id || '',
      characterName: data.character_name || data.characterName || '',
      content: '',
      isStreaming: true,
      timestamp: normalizeTimestamp(data.timestamp),
    })
    return
  }

  if (data.type === 'stream_delta') {
    appendStreamDelta(data.id, data.delta || '')
    return
  }

  if (data.type === 'stream_end') {
    updateSortedMessages(msgs => {
      const exists = msgs.some(m => m.id === data.id)
      const finalized = withNormalizedTimestamp({
        id: data.id,
        type: 'chat',
        senderType: data.sender_type || 'character',
        senderId: data.sender_id || data.character_id || '',
        characterName: data.character_name || data.characterName || '',
        content: data.content ?? '',
        action: data.action,
        innerThought: data.inner_thought || data.innerThought || '',
        timestamp: data.timestamp,
        isStreaming: false,
      })
      if (!exists) return [...msgs, finalized]
      return msgs.map(m => m.id === data.id ? { ...m, ...finalized } : m)
    })
    messages.update(msgs => {
      if (!msgs.some(m => m.isStreaming)) {
        isStreamingReply.set(false)
      }
      return msgs
    })
    if (view === 'private') {
      lastPrivateMsgTimestamp.set(Date.now())
    }
    return
  }

  if (data.type === 'typing') {
    typingCharacters.update(list => {
      if (list.some(c => c.id === data.character_id)) return list
      return [...list, { id: data.character_id, name: data.character_name || data.character_id }]
    })
    return
  }

  if (data.type === 'typing_end') {
    typingCharacters.update(list => list.filter(c => c.id !== data.character_id))
    return
  }

  if (data.type === 'image_generating') {
    typingCharacters.update(list => {
      if (list.some(c => c.id === data.character_id)) return list
      const charList = get(characters)
      const found = charList.find(c => c.id === data.character_id)
      return [...list, {
        id: data.character_id,
        name: (found?.name || data.character_id) + ' · 发送照片中',
      }]
    })
    if (data.job_id) {
      imageJobs.update(jobs => ({
        ...jobs,
        [data.job_id]: {
          job_id: data.job_id,
          character_id: data.character_id,
          status: 'queued',
          progress_text: '排队中',
        },
      }))
    }
    return
  }

  if (data.type === 'image_job_update') {
    imageJobs.update(jobs => ({
      ...jobs,
      [data.job_id]: {
        ...jobs[data.job_id],
        ...data,
      },
    }))
    const active = ['queued', 'generating', 'uploading', 'retrying'].includes(data.status)
    if (active) {
      typingCharacters.update(list => {
        if (list.some(c => c.id === data.character_id)) return list
        const charList = get(characters)
        const found = charList.find(c => c.id === data.character_id)
        const label = data.progress_text || '发送照片中'
        return [...list, {
          id: data.character_id,
          name: (found?.name || data.character_name || data.character_id) + ` · ${label}`,
        }]
      })
    } else {
      typingCharacters.update(list => list.filter(c => c.id !== data.character_id))
    }
    return
  }

  if (data.type === 'image_ready') {
    isWaitingReply.set(false)
    typingCharacters.update(list => list.filter(c => c.id !== data.character_id))
    if (data.job_id) {
      imageJobs.update(jobs => {
        const next = { ...jobs }
        if (next[data.job_id]) {
          next[data.job_id] = { ...next[data.job_id], status: 'completed', url: data.url }
        }
        return next
      })
    }
    const charList = get(characters)
    const found = charList.find(c => c.id === data.character_id)
    updateSortedMessages(msgs => [...msgs, withNormalizedTimestamp({
      id: data.message_id,
      type: 'chat',
      senderType: 'character',
      senderId: data.character_id,
      characterName: found?.name || data.character_id,
      content: data.url,
      contentType: 'image',
      timestamp: Date.now(),
    })])
    if (view === 'private') {
      lastPrivateMsgTimestamp.set(Date.now())
    }
    return
  }

  if (data.type === 'reply_batch_end') {
    isWaitingReply.set(false)
    isStreamingReply.set(false)
    typingCharacters.set([])
    return
  }

  if (data.type === 'message') {
    if (view === 'private') {
      isWaitingReply.set(false)
    }
    if (data.sender_type === 'user') {
      updateSortedMessages(msgs => {
        if (data.client_id) {
          const idx = msgs.findIndex(m => m.id === data.client_id)
          if (idx >= 0) {
            const next = [...msgs]
            next[idx] = {
              ...next[idx],
              id: data.id,
              content: data.content ?? next[idx].content,
              timestamp: normalizeTimestamp(data.timestamp ?? next[idx].timestamp),
              isStreaming: false,
            }
            return next
          }
        }
        if (msgs.some(m => m.id === data.id)) return msgs
        return [...msgs, {
          id: data.id,
          type: 'chat',
          senderType: 'user',
          senderId: 'user',
          content: data.content,
          timestamp: normalizeTimestamp(data.timestamp),
        }]
      })
      if (view === 'private') {
        isWaitingReply.set(true)
      }
      return
    }
    if (get(messages).some(m => m.id === data.id)) {
      upsertMessage(data.id, {
          senderType: data.sender_type || data.senderType,
          senderId: data.sender_id || data.senderId,
          characterName: data.character_name || data.characterName || '',
          content: data.content,
          action: data.action,
          innerThought: data.inner_thought || data.innerThought || '',
          timestamp: normalizeTimestamp(data.timestamp),
          isStreaming: false,
      })
      if (view === 'private') {
        lastPrivateMsgTimestamp.set(Date.now())
      }
      return
    }
    updateSortedMessages(msgs => [...msgs, withNormalizedTimestamp({
      id: data.id,
      type: 'chat',
      senderType: data.sender_type || data.senderType,
      senderId: data.sender_id || data.senderId,
      characterName: data.character_name || data.characterName || '',
      content: data.content,
      action: data.action,
      innerThought: data.inner_thought || data.innerThought || '',
      timestamp: data.timestamp,
    })])
    if (view === 'private') {
      lastPrivateMsgTimestamp.set(Date.now())
    }
    return
  }

  if (data.type === 'error') {
    isWaitingReply.set(false)
    isStreamingReply.set(false)
    typingCharacters.set([])
    messages.update(msgs => [
      ...msgs.map(m => m.isStreaming
        ? { ...m, isStreaming: false, content: m.content || '（回复中断）' }
        : m),
      { type: 'system', content: `错误：${data.message}` },
    ])
  }
}

export async function connect(view, id) {
  if (!view || !id) return

  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }

  if (ws && ws.readyState === WebSocket.OPEN && currentView === view && currentId === id) {
    return
  }

  const scopeSeq = ++connectSeq
  intentionalClose = true
  teardownSocket(ws)
  ws = null
  intentionalClose = false

  currentView = view
  currentId = id
  historyLoadedFor = null
  setActiveLlmScope(view, id)
  if (view === 'group') {
    activeGroupId.set(id)
  } else {
    activeGroupId.set(null)
    activeGroup.set(null)
  }
  isWaitingReply.set(false)
  isStreamingReply.set(false)
  typingCharacters.set([])
  isLoadingHistory.set(true)

  try {
    if (view === 'private') {
      await loadPrivateHistory(id, { scopeSeq, view, id })
    } else {
      await loadGroupHistory(id, { scopeSeq, view, id })
    }
  } finally {
    if (scopeSeq === connectSeq) {
      isLoadingHistory.set(false)
    }
  }

  if (scopeSeq !== connectSeq) return

  const url = view === 'group'
    ? wsUrl(`/ws/group/${id}`)
    : wsUrl(`/ws/chat/${id}`)

  isConnecting.set(true)
  connectionStatus.set('connecting')

  const socket = new WebSocket(url)
  ws = socket

  socket.onopen = () => {
    if (socket !== ws) return
    reconnectFailures = 0
    isConnecting.set(false)
    connectionStatus.set('connected')
    bindWebSocket(socket)
  }

  socket.onmessage = (event) => {
    if (socket !== ws) return
    const data = JSON.parse(event.data)
    handleMessage(data, view)
  }

  socket.onclose = () => {
    if (socket !== ws) return
    connectionStatus.set('disconnected')
    isConnecting.set(false)
    bindWebSocket(null)
    const waiting = get(isWaitingReply) || get(isStreamingReply)
    isWaitingReply.set(false)
    isStreamingReply.set(false)
    typingCharacters.set([])
    if (intentionalClose) return
    if (waiting) {
      messages.update(msgs => [...msgs, {
        type: 'system',
        content: '连接中断，回复可能仍在生成。请稍等后刷新历史，或重新发送。',
      }])
      return
    }
    reconnectFailures += 1
    const delay = Math.min(3000 * (2 ** Math.min(reconnectFailures - 1, 4)), 30000)
    if (reconnectFailures === 1) {
      messages.update(msgs => [...msgs, {
        type: 'system',
        content: '连接已断开，正在尝试重连…（请确认后端已在 :8000 启动）',
      }])
    }
    reconnectTimer = setTimeout(async () => {
      if (currentView !== view || currentId !== id) return
      try {
        const res = await fetch(apiUrl('/api/health'), { cache: 'no-store' })
        if (!res.ok) return
      } catch {
        return
      }
      connect(currentView, currentId)
    }, delay)
  }

  socket.onerror = () => {
    if (socket !== ws) return
    connectionStatus.set('disconnected')
    isConnecting.set(false)
    isWaitingReply.set(false)
    isStreamingReply.set(false)
    typingCharacters.set([])
  }
}

export function sendMessage(content) {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    messages.update(msgs => [...msgs, { type: 'system', content: '未连接，无法发送' }])
    return
  }

  const clientId = `local_${Date.now()}`
  updateSortedMessages(msgs => [...msgs, {
    id: clientId,
    type: 'chat',
    senderType: 'user',
    senderId: 'user',
    content,
    timestamp: getWorldNowMs(),
  }])

  isWaitingReply.set(true)

  const payload = {
    message: content,
    llm: getCurrentLlmPayload(),
    client_id: clientId,
  }
  // V4.2：不再发送持久化聊天/叙述模式；场景由服务端按本轮内容判断

  ws.send(JSON.stringify(payload))
}

export function setChatMode(mode) {
  if (mode !== 'chat' && mode !== 'scene') return
  chatMode.set(mode)
  if (ws && ws.readyState === WebSocket.OPEN && currentView === 'private') {
    ws.send(JSON.stringify({ type: 'set_mode', mode }))
    return
  }
  fetch(apiUrl('/api/v4/mode'), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode }),
  }).catch(err => console.error('保存模式失败:', err))
}

function messageApiPath(messageId) {
  const view = get(activeView)
  if (view === 'group') {
    const gid = get(activeGroupId)
    return apiUrl(`/api/group/${gid}/messages/${messageId}`)
  }
  const cid = get(activeCharacterId)
  return apiUrl(`/api/chat/${cid}/messages/${messageId}`)
}

export async function editMessage(messageId, content) {
  try {
    const res = await fetch(messageApiPath(messageId), {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || '编辑失败')
    }
    const data = await res.json()
    messages.update(msgs => msgs.map(m =>
      m.id === messageId
        ? { ...m, content: data.content, edited: true }
        : m
    ))
    return true
  } catch (e) {
    messages.update(msgs => [...msgs, { type: 'system', content: e.message || '编辑失败' }])
    return false
  }
}

export async function deleteMessage(messageId) {
  try {
    const res = await fetch(messageApiPath(messageId), { method: 'DELETE' })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || '删除失败')
    }
    messages.update(msgs => msgs.filter(m => m.id !== messageId))
    return true
  } catch (e) {
    messages.update(msgs => [...msgs, { type: 'system', content: e.message || '删除失败' }])
    return false
  }
}

export function regenerateReply(messageId) {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    messages.update(msgs => [...msgs, { type: 'system', content: '未连接，无法重新生成' }])
    return
  }
  const msg = get(messages).find(m => m.id === messageId)
  if (!msg || msg.senderType === 'user' || msg.isStreaming) return
  if (get(isWaitingReply) || get(isStreamingReply)) {
    messages.update(msgs => [...msgs, { type: 'system', content: '请等待当前回复完成' }])
    return
  }

  messages.update(msgs => msgs.map(m =>
    m.id === messageId
      ? { ...m, content: '', innerThought: '', isStreaming: true }
      : m
  ))
  isWaitingReply.set(true)
  isStreamingReply.set(true)

  ws.send(JSON.stringify({
    type: 'regenerate',
    message_id: messageId,
    llm: getCurrentLlmPayload(),
  }))
}

export async function refreshActiveChat() {
  const view = get(activeView)
  const id = view === 'group' ? get(activeGroupId) : get(activeCharacterId)
  if (!view || !id) return

  if (view === 'private') {
    await loadPrivateHistory(id, { scopeSeq: connectSeq, view: 'private', id })
  } else if (view === 'group') {
    await loadGroupHistory(id, { scopeSeq: connectSeq, view: 'group', id })
  }

  isWaitingReply.set(false)
  isStreamingReply.set(false)
  typingCharacters.set([])

  if (!ws || ws.readyState !== WebSocket.OPEN) {
    await connect(view, id)
  }
}

export function disconnect() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  intentionalClose = true
  teardownSocket(ws)
  ws = null
  connectSeq += 1
  reconnectFailures = 0
  connectionStatus.set('disconnected')
  isConnecting.set(false)
  isWaitingReply.set(false)
  isStreamingReply.set(false)
  typingCharacters.set([])
  bindWebSocket(null)
}

/** Request AI character photo via V4 image engine (private chat only). */
export function requestCharacterPhoto(hint = '') {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    messages.update(msgs => [...msgs, { type: 'system', content: '未连接，无法生成照片' }])
    return false
  }
  if (currentView !== 'private' || !currentId) {
    messages.update(msgs => [...msgs, { type: 'system', content: '请在私聊中使用生图' }])
    return false
  }
  ws.send(JSON.stringify({
    type: 'generate_image',
    hint: hint || '自然放松的肖像，看向镜头',
    priority: 'quality',
  }))
  return true
}
