/** UI permissions. The API enforces the same names and ignores this file. */

export const OCCUPANCY_READ = 'occupancy.read'
export const SESSIONS_READ = 'sessions.read'
export const GATE_READ = 'gate.read'
export const GATE_OPERATE = 'gate.operate'
export const RESERVATIONS_READ = 'reservations.read'
export const RESERVATIONS_MANAGE = 'reservations.manage'
export const RESERVATIONS_REQUESTS_READ = 'reservations.requests.read'
export const RESERVATIONS_REQUESTS_CREATE = 'reservations.requests.create'
export const RESERVATIONS_APPROVE = 'reservations.approve'
export const RESERVATIONS_REJECT = 'reservations.reject'
export const SETTINGS_READ = 'settings.read'
export const SETTINGS_MANAGE = 'settings.manage'
export const PRICING_READ = 'pricing.read'
export const PRICING_QUOTE = 'pricing.quote'

const ALL = [
  OCCUPANCY_READ,
  SESSIONS_READ,
  GATE_READ,
  GATE_OPERATE,
  RESERVATIONS_READ,
  RESERVATIONS_MANAGE,
  RESERVATIONS_REQUESTS_READ,
  RESERVATIONS_REQUESTS_CREATE,
  RESERVATIONS_APPROVE,
  RESERVATIONS_REJECT,
  SETTINGS_READ,
  SETTINGS_MANAGE,
  PRICING_READ,
  PRICING_QUOTE,
] as const

const ROLE_PERMISSIONS: Record<string, readonly string[]> = {
  admin: ALL,
  employee: [
    OCCUPANCY_READ,
    RESERVATIONS_REQUESTS_READ,
    RESERVATIONS_APPROVE,
    RESERVATIONS_REJECT,
  ],
}

export function permissionsForRole(role: string | undefined): ReadonlySet<string> {
  return new Set(ROLE_PERMISSIONS[role ?? ''] ?? [])
}

export function can(role: string | undefined, permission: string): boolean {
  return permissionsForRole(role).has(permission)
}

export function routePermission(pathname: string): string | null {
  if (pathname === '/' || pathname.startsWith('/parking-map') || pathname.startsWith('/analytics')) {
    return OCCUPANCY_READ
  }
  if (pathname.startsWith('/sessions')) return SESSIONS_READ
  if (pathname.startsWith('/reservations')) return RESERVATIONS_REQUESTS_READ
  if (pathname.startsWith('/settings')) return SETTINGS_READ
  return null
}

export function canVisit(role: string | undefined, pathname: string): boolean {
  const permission = routePermission(pathname)
  if (permission === null) return false
  return can(role, permission)
}
