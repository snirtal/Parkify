import type { ParkingBay } from '../../types/parking'

function normalizeToken(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]/g, '')
}

export function matchBayQuery(bay: ParkingBay, rawQuery: string): boolean {
  const trimmed = rawQuery.trim()
  if (!trimmed) return true

  const normQuery = normalizeToken(trimmed)
  if (!normQuery) return true

  const normCode = normalizeToken(bay.code)
  const normPlate = bay.vehicle ? normalizeToken(bay.vehicle.plateNumber) : ''

  return normCode.includes(normQuery) || normPlate.includes(normQuery)
}
