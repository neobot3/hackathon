export const ROLES = Object.freeze({
  ADMIN: 'admin',
  SCHEDULER: 'scheduler',
  // Tech rep (team member): read-only dashboards plus their own balances.
  REP: 'rep',
  // Other users: read-only dashboards without training or balances.
  VIEWER: 'viewer',
})

// Admins can do everything a scheduler can.
export function hasRole(user, role) {
  if (!user) return false
  return user.roles.includes(role) || (role === ROLES.SCHEDULER && user.roles.includes(ROLES.ADMIN))
}

export function hasAnyRole(user, roles) {
  return roles.some((role) => hasRole(user, role))
}
