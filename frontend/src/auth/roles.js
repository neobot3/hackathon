export const ROLES = Object.freeze({
  ADMIN: 'admin',
  SCHEDULER: 'scheduler',
})

// Admins can do everything a scheduler can.
export function hasRole(user, role) {
  if (!user) return false
  return user.roles.includes(role) || (role === ROLES.SCHEDULER && user.roles.includes(ROLES.ADMIN))
}
