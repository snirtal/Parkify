import { describe, expect, it } from 'vitest'
import { NAV_ITEMS } from '../config/navigation'
import {
  RESERVATIONS_APPROVE,
  canVisit,
  permissionsForRole,
} from './permissions'

function visiblePaths(role: string) {
  const granted = permissionsForRole(role)
  return NAV_ITEMS.filter((item) => granted.has(item.permission)).map((item) => item.path)
}

describe('navigation permissions', () => {
  it('shows every section to an admin and occupancy pages to an employee', () => {
    expect(visiblePaths('admin')).toEqual(NAV_ITEMS.map((item) => item.path))
    expect(visiblePaths('employee')).toEqual(['/', '/parking-map', '/reservations', '/analytics'])
    expect(visiblePaths('contractor')).toEqual([])
  })

  it('blocks direct navigation to restricted pages', () => {
    expect(canVisit('employee', '/')).toBe(true)
    expect(canVisit('employee', '/parking-map')).toBe(true)
    expect(canVisit('employee', '/analytics')).toBe(true)
    expect(canVisit('employee', '/sessions')).toBe(false)
    expect(canVisit('employee', '/reservations')).toBe(true)
    expect(canVisit('employee', '/settings')).toBe(false)
    expect(canVisit('admin', '/settings')).toBe(true)
    expect(canVisit('admin', '/reservations')).toBe(true)
    expect(permissionsForRole('employee').has(RESERVATIONS_APPROVE)).toBe(true)
  })
})
