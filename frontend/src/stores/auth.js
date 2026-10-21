import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { authProvider } from '@/auth'
import { hasAnyRole, hasRole, ROLES } from '@/auth/roles'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const ready = ref(false)

  const isAuthenticated = computed(() => !!user.value)
  const isAdmin = computed(() => hasRole(user.value, ROLES.ADMIN))
  const isScheduler = computed(() => hasRole(user.value, ROLES.SCHEDULER))
  const isRep = computed(() => hasRole(user.value, ROLES.REP))
  const homeRoute = computed(() => (isAdmin.value ? '/admin' : isScheduler.value ? '/scheduler' : '/dashboards'))
  const roleLabel = computed(() =>
    isAdmin.value ? 'Admin' : isScheduler.value ? 'Scheduler' : isRep.value ? 'Tech rep' : 'Viewer',
  )

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

  function canAny(roles) {
    return hasAnyRole(user.value, roles)
  }

  return { user, ready, isAuthenticated, isAdmin, isScheduler, isRep, homeRoute, roleLabel, init, login, logout, can, canAny }
})
