import { http } from './http'

export const agentApi = {
  encourage(payload) {
    return http.post('/agent/encourage', payload)
  },
  report(useLlm = true) {
    return http.get('/agent/report', { use_llm: useLlm })
  },
  createPlan(payload) {
    return http.post('/agent/plan', payload)
  },
  plans() {
    return http.get('/agent/plans')
  },
  chat(payload) {
    return http.post('/agent/chat', payload)
  },
}