import { createContext, useContext } from 'react'
import type {
  FacilitySettings,
  ReservationDraft,
  ReservationItem,
  SmartParkingDataset,
} from '../types/parking'

export type ActionResult = { ok: true } | { ok: false; error: string }
export type ReservationActionResult = ActionResult

export interface ParkingContextValue {
  dataset: SmartParkingDataset
  reservations: ReservationItem[]
  settings: FacilitySettings
  addReservation: (draft: ReservationDraft) => ReservationActionResult
  updateReservation: (id: string, draft: ReservationDraft) => ReservationActionResult
  cancelReservation: (id: string) => void
  updateSettings: (next: FacilitySettings) => ActionResult
  resetSettings: () => FacilitySettings
}

export const ParkingContext = createContext<ParkingContextValue | null>(null)

export function useParkingState(): ParkingContextValue {
  const ctx = useContext(ParkingContext)
  if (!ctx) {
    throw new Error('useParkingState must be used within a ParkingStateProvider')
  }
  return ctx
}
