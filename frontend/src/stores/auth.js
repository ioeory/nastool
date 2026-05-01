import { defineStore } from 'pinia'
import { authApi } from '@/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: null,
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    isSuperuser: (state) => state.user?.is_superuser || false,
  },

  actions: {
    async login(username, password) {
      const res = await authApi.login(username, password)
      this.token = res.access_token
      localStorage.setItem('token', this.token)
      await this.fetchMe()
    },

    async fetchMe() {
      try {
        const res = await authApi.me()
        this.user = res.data
      } catch {
        this.logout()
      }
    },

    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
    },
  },
})
