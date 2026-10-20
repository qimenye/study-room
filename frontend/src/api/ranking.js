import { http } from './http'

export const rankingApi = {
  list(period = 'today', limit = 50) {
    return http.get('/ranking', { period, limit })
  },
}