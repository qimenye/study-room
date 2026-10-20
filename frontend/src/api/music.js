import { getToken, http } from './http'

export const musicApi = {
  search: (q, limit = 20, offset = 0) => http.get('/music/search', { q, limit, offset }),
  settings: () => http.get('/settings/music'),
  saveSettings: (payload) => http.put('/settings/music', payload),
  clearSettings: () => http.delete('/settings/music'),
  testSettings: (payload) => http.post('/settings/music/test', payload),
  loginQr: () => http.post('/music/login/qr'),
  qrStatus: (key, session) => http.get('/music/login/qr/status', { key, session }),
  sendCaptcha: (payload) => http.post('/music/login/captcha', payload),
  phoneLogin: (payload) => http.post('/music/login/phone', payload),
  /** <audio> 带不了 Authorization 头，token 只能放 query；后端也支持 Bearer。 */
  streamUrl: (id) => '/api/music/stream/' + encodeURIComponent(id) + '?token=' + encodeURIComponent(getToken()),
}
