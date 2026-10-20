import { http } from './http'

export const authApi = {
  register(payload) {
    return http.post('/auth/register', payload)
  },
  login(payload) {
    return http.post('/auth/login', payload)
  },
  me() {
    return http.get('/users/me')
  },
  updateMe(payload) {
    return http.patch('/users/me', payload)
  },
  health() {
    return http.get('/health')
  },
}