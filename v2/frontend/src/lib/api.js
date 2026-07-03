/** API / WebSocket base URLs — dev 模式下 API/WS 直连后端 :8000，绕过 Vite 代理。 */

const BACKEND_PORT = 8000

function isLocalHost(hostname) {
  return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '[::1]'
}

/** Dev 或直连后端 :8000 时使用绝对 URL；生产经 Nginx 反代时用相对路径。 */
export function useDirectBackend() {
  if (typeof window === 'undefined') return false
  if (import.meta.env.DEV) return true
  const port = window.location.port
  return port === '8000' || port === '8000/'
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
