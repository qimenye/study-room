// 计时放进 Web Worker：后台标签页不会被浏览器节流到 1 秒以上。
// 计时基于 Date.now() 差值累加，避免 setInterval 漂移。
let timerId = null
let lastTs = 0
let elapsed = 0
let running = false

function tick() {
  const now = Date.now()
  const delta = Math.floor((now - lastTs) / 1000)
  if (delta <= 0) return
  lastTs += delta * 1000
  elapsed += delta
  postMessage({ type: 'tick', elapsed })
}

self.onmessage = (event) => {
  const data = event.data || {}
  switch (data.type) {
    case 'start':
      if (running) break
      running = true
      lastTs = Date.now()
      timerId = setInterval(tick, 200)
      postMessage({ type: 'started', elapsed })
      break
    case 'pause':
      running = false
      if (timerId) clearInterval(timerId)
      timerId = null
      postMessage({ type: 'paused', elapsed })
      break
    case 'sync':
      elapsed = Math.max(0, Math.floor(data.elapsed || 0))
      lastTs = Date.now()
      postMessage({ type: 'synced', elapsed })
      break
    case 'reset':
      running = false
      if (timerId) clearInterval(timerId)
      timerId = null
      elapsed = 0
      postMessage({ type: 'reset' })
      break
    default:
      break
  }
}