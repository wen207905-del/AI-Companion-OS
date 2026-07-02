/** API / WebSocket base URLs — dev 模式下 API/WS 直连后端 :8000，绕过 Vite 代理。 */

const BACKEND_PORT = 8000

function isLocalHost(hostname) {
  return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '[::1]'
}

/** Dev 模式统一直连 :8000，PC/手机行为一致，避免 Vite 代理 WS/HTTP 异常。 */
export function useDirectBackend() {
  if (typeof window === 'undefined') return false
  return import.meta.env.DEV || !isLocalHost(window.location.hostname)
}

function backendOrigin() {
  const protocol = window.location.protocol
  const host = window.location.hostname
  return `${protocol}//${host}:${BACKEND_PORT}`
}

/** REST path, e.g. apiUrl('/api/characters') */
export function apiUrl(path) {
  if (useDirectBackend()) {
    return `${backendOrigin()}${path}`
  }
  return path
}

/** WebSocket path, e.g. wsUrl('/ws/chat/bai_rou') */
export function wsUrl(path) {
  if (useDirectBackend()) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.hostname
    return `${protocol}//${host}:${BACKEND_PORT}${path}`
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const port = window.location.port ? `:${window.location.port}` : ''
  return `${protocol}//${window.location.hostname}${port}${path}`
}
