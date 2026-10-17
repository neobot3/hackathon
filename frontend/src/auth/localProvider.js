import { ROLES } from './roles'

// TEMPORARY demo accounts until Azure SSO is enabled (VITE_AUTH_MODE=azure).
// These credentials ship in the browser bundle and protect nothing; the API itself is not secured yet.
const DEMO_USERS = [
  { username: 'admin', password: 'admin123', name: 'Alex Admin', roles: [ROLES.ADMIN] },
  { username: 'scheduler', password: 'scheduler123', name: 'Sam Scheduler', roles: [ROLES.SCHEDULER] },
]

const STORAGE_KEY = 'techrep.session'

export const demoAccounts = DEMO_USERS.map(({ username, password, roles }) => ({ username, password, roles }))

export const localProvider = {
  async init() {
    try {
      return JSON.parse(sessionStorage.getItem(STORAGE_KEY)) || null
    } catch {
      return null
    }
  },

  async login({ username, password }) {
    const match = DEMO_USERS.find(
      (u) => u.username === username.trim().toLowerCase() && u.password === password,
    )
    if (!match) throw new Error('Invalid username or password')
    const user = { username: match.username, name: match.name, roles: [...match.roles] }
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(user))
    return user
  },

  async logout() {
    sessionStorage.removeItem(STORAGE_KEY)
  },

  async getAccessToken() {
    return null
  },
}
