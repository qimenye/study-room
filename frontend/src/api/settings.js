import { http } from './http'

export const settingsApi = {
  /** 读取模型设置：只回掩码，不含明文 Key */
  llm: () => http.get('/settings/llm'),
  /** api_key 不传 = 保持原样，传空串 = 清除 */
  saveLlm: (payload) => http.put('/settings/llm', payload),
  clearLlm: () => http.delete('/settings/llm'),
  testLlm: (payload) => http.post('/settings/llm/test', payload),
}
