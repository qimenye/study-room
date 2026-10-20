import { http } from './http'

export const roomsApi = {
  list(topic) {
    return http.get('/rooms', { topic })
  },
  create(payload) {
    return http.post('/rooms', payload)
  },
  detail(roomId) {
    return http.get('/rooms/' + roomId)
  },
  remove(roomId) {
    return http.delete('/rooms/' + roomId)
  },
  join(roomId) {
    return http.post('/rooms/' + roomId + '/join')
  },
  leave(roomId) {
    return http.post('/rooms/' + roomId + '/leave')
  },
}