import { defineStore } from 'pinia'

import { authApi } from '../api/auth'
import { getToken, setToken } from '../api/http'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: getToken(),
    profile: null,
    loading: false,
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.token),
    displayName: (state) => state.profile?.nickname || state.profile?.username || '',
  },
  actions: {
    async login(payload) {
      const data = await authApi.login(payload)
      this.token = data.access_token
      setToken(this.token)
      this.profile = data.user
      return data.user
    },
    async register(payload) {
      const data = await authApi.register(payload)
      this.token = data.access_token
      setToken(this.token)
      this.profile = data.user
      return data.user
    },
    async fetchMe() {
      if (!this.token) return null
      this.loading = true
      try {
        this.profile = await authApi.me()
        return this.profile
      } catch (error) {
        this.logout()
        return null
      } finally {
        this.loading = false
      }
    },
    async refresh() {
      return this.fetchMe()
    },
    logout() {
      this.token = ''
      this.profile = null
      setToken('')
    },
  },
})