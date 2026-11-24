import type { ParkingBay } from '../../types/parking'

export function normalizeSearchToken(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]/g, '')
}

export function matchesCodeOrPlate(
  spaceCode: string,
  plateNumber: string | undefined,
  rawQuery: string,
): boolean {
  const trimmed = rawQuery.trim()
  if (!trimmed) return true

  const normQuery = normalizeSearchToken(trimmed)
  if (!normQuery) return true

  const normCode = normalizeSearchToken(spaceCode)
  const normPlate = plateNumber ? normalizeSearchToken(plateNumber) : ''

  return normCode.includes(normQuery) || normPlate.includes(normQuery)
}

export function matchBayQuery(bay: ParkingBay, rawQuery: string): boolean {
  return matchesCodeOrPlate(bay.code, bay.vehicle?.plateNumber, rawQuery)
}
