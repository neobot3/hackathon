import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { authProvider } from '@/auth'
import { hasRole, ROLES } from '@/auth/roles'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const ready = ref(false)

  const isAuthenticated = computed(() => !!user.value)
  const isAdmin = computed(() => hasRole(user.value, ROLES.ADMIN))
  const isScheduler = computed(() => hasRole(user.value, ROLES.SCHEDULER))
  const homeRoute = computed(() => (isAdmin.value ? '/admin' : '/scheduler'))

  async function init() {
    if (ready.value) return
    user.value = await authProvider.init()
    ready.value = true
  }

  async function login(credentials) {
    user.value = await authProvider.login(credentials)
    return user.value
  }

  async function logout() {
    await authProvider.logout()
    user.value = null
  }

  function can(role) {
    return hasRole(user.value, role)
  }

  return { user, ready, isAuthenticated, isAdmin, isScheduler, homeRoute, init, login, logout, can }
})
