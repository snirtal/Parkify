import type { ParkingBay } from '../types/parking'

export interface BayPlacement {
  deck: ParkingBay['deck']
  row: ParkingBay['row']
  slotIndex: number
}

/**
 * The API returns spot codes and status, not the row or slot used by the 3D map.
 * This numbering is the existing garage layout: six stalls per row.
 */
export function placementForCode(code: string): BayPlacement | null {
  const number = Number(code.replace(/\D/g, ''))
  if (!Number.isInteger(number)) return null
  const deck: ParkingBay['deck'] | null =
    number >= 201 && number <= 212 ? 'P2' : number >= 101 && number <= 112 ? 'P1' : null
  if (deck === null) return null
  const index = number - (deck === 'P2' ? 201 : 101)
  return {
    deck,
    row: index < 6 ? 'north' : 'south',
    slotIndex: index % 6,
  }
}
