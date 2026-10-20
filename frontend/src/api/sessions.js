import { http } from './http'

export const sessionsApi = {
  start(payload) {
    return http.post('/sessions/start', payload)
  },
  pause(sessionId) {
    return http.post('/sessions/' + sessionId + '/pause')
  },
  resume(sessionId) {
    return http.post('/sessions/' + sessionId + '/resume')
  },
  end(sessionId) {
    return http.post('/sessions/' + sessionId + '/end')
  },
  active() {
    return http.get('/sessions/active')
  },
  records(period = 'week', limit = 100) {
    return http.get('/sessions/records', { period, limit })
  },
  stats() {
    return http.get('/sessions/stats')
  },
  heatmap(days = 180) {
    return http.get('/sessions/heatmap', { days })
  },
}