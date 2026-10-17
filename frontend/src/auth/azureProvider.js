import { config } from '@/config'
import { ROLES } from './roles'

const NOT_READY = 'Azure SSO is not enabled yet. Set VITE_AUTH_MODE=local or finish azureProvider.js.'

// Maps Entra ID token claims (app roles) to the UI user shape used by the auth store.
export function userFromClaims(claims) {
  const roles = []
  const tokenRoles = claims.roles || []
  if (tokenRoles.includes(config.azure.adminRole)) roles.push(ROLES.ADMIN)
  if (tokenRoles.includes(config.azure.schedulerRole)) roles.push(ROLES.SCHEDULER)
  return {
    username: claims.preferred_username || claims.email || claims.oid,
    name: claims.name || claims.preferred_username,
    roles,
  }
}

// Same interface as localProvider. Implement with @azure/msal-browser:
// init -> handleRedirectPromise, login -> loginRedirect, getAccessToken -> acquireTokenSilent(apiScope).
export const azureProvider = {
  async init() {
    return null
  },
  async login() {
    throw new Error(NOT_READY)
  },
  async logout() {},
  async getAccessToken() {
    return null
  },
}
