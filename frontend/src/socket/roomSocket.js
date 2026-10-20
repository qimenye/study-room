import { getToken } from '../api/http'

/**
 * 房间 WebSocket 封装：
 * - 自动重连（指数退避）
 * - 心跳 ping（服务端 60 秒无心跳会判定离线）
 * - 事件订阅式 API，避免页面里写一堆 if
 */
export function createRoomSocket() {
  let socket = null
  let roomId = null
  let closedByUser = false
  let retry = 0
  let heartbeat = null
  let reconnectTimer = null
  const listeners = new Map()

  function emit(type, payload) {
    const handlers = listeners.get(type)
    if (handlers) handlers.forEach((handler) => handler(payload))
  }

  function on(type, handler) {
    if (!listeners.has(type)) listeners.set(type, new Set())
    listeners.get(type).add(handler)
    return () => listeners.get(type)?.delete(handler)
  }

  function send(message) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(message))
      return true
    }
    return false
  }

  function buildUrl(id) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const token = encodeURIComponent(getToken())
    return protocol + '//' + window.location.host + '/ws/room/' + id + '?token=' + token
  }

  function startHeartbeat() {
    stopHeartbeat()
    heartbeat = setInterval(() => send({ type: 'ping' }), 25000)
  }

  function stopHeartbeat() {
    if (heartbeat) clearInterval(heartbeat)
    heartbeat = null
  }

  function connect(id) {
    if (!id) return
    roomId = id
    closedByUser = false
    cleanup()

    socket = new WebSocket(buildUrl(id))

    socket.onopen = () => {
      retry = 0
      startHeartbeat()
      emit('open')
    }

    socket.onmessage = (event) => {
      let data = null
      try {
        data = JSON.parse(event.data)
      } catch {
        return
      }
      if (data && data.type) emit(data.type, data)
    }

    socket.onclose = (event) => {
      stopHeartbeat()
      emit('close', event)
      if (closedByUser) return
      retry += 1
      const delay = Math.min(15000, 1000 * Math.pow(1.6, retry))
      reconnectTimer = setTimeout(() => connect(roomId), delay)
    }

    socket.onerror = () => emit('error')
  }

  function cleanup() {
    if (socket) {
      socket.onopen = null
      socket.onmessage = null
      socket.onclose = null
      socket.onerror = null
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close()
      }
    }
    socket = null
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectTimer = null
  }

  function close() {
    closedByUser = true
    stopHeartbeat()
    cleanup()
  }

  return { connect, close, send, on, get roomId() { return roomId } }
}