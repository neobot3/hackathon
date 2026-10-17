const env = import.meta.env

export const config = {
  appName: env.VITE_APP_NAME || 'TechRep Scheduler',
  apiBaseUrl: (env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, ''),
  authMode: env.VITE_AUTH_MODE === 'azure' ? 'azure' : 'local',
  azure: {
    clientId: env.VITE_AZURE_CLIENT_ID || '',
    tenantId: env.VITE_AZURE_TENANT_ID || '',
    authority: env.VITE_AZURE_AUTHORITY || '',
    redirectUri: env.VITE_AZURE_REDIRECT_URI || `${window.location.origin}/auth/callback`,
    postLogoutRedirectUri: env.VITE_AZURE_POST_LOGOUT_REDIRECT_URI || window.location.origin,
    apiScope: env.VITE_AZURE_API_SCOPE || '',
    adminRole: env.VITE_AZURE_ADMIN_ROLE || 'TechRep.Admin',
    schedulerRole: env.VITE_AZURE_SCHEDULER_ROLE || 'TechRep.Scheduler',
  },
}
