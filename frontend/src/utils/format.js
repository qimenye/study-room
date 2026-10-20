/**
 * 后端返回的是 UTC 朴素时间字符串（没有时区后缀，例如 2026-10-05T12:00:00）。
 * JS 的 new Date(x) 会把这种字符串当成本地时间，导致 8 小时偏差。
 * 所以统一用 parseUtc 解析。
 */
export function parseUtc(value) {
  if (!value) return null
  if (value instanceof Date) return value
  const text = String(value)
  const hasZone = /(Z|[+-]\d{2}:?\d{2})$/.test(text)
  const date = new Date(hasZone ? text : text + 'Z')
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatDuration(seconds) {
  const total = Math.max(0, Math.floor(seconds || 0))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  if (hours > 0) return hours + ' 小时 ' + minutes + ' 分'
  if (minutes > 0) return minutes + ' 分钟'
  return total + ' 秒'
}

export function formatClock(seconds) {
  const total = Math.max(0, Math.floor(seconds || 0))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const secs = total % 60
  const mm = String(minutes).padStart(2, '0')
  const ss = String(secs).padStart(2, '0')
  return hours > 0 ? String(hours) + ':' + mm + ':' + ss : mm + ':' + ss
}

export function formatDateTime(value) {
  const date = parseUtc(value)
  if (!date) return '-'
  return date.toLocaleString('zh-CN', { hour12: false })
}

export function statusLabel(status) {
  return { focusing: '专注中', resting: '休息', away: '离开' }[status] || status
}

export function statusColor(status) {
  return (
    {
      focusing: 'text-calm border-calm/40 bg-calm/10',
      resting: 'text-slate-300 border-line bg-white/5',
      away: 'text-slate-500 border-line bg-transparent',
    }[status] || 'text-slate-400 border-line'
  )
}