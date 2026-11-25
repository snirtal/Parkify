import { createContext, useContext } from 'react'
import type {
  ReservationDraft,
  ReservationItem,
  SmartParkingDataset,
} from '../types/parking'

export type ReservationActionResult =
  | { ok: true }
  | { ok: false; error: string }

export interface ParkingContextValue {
  dataset: SmartParkingDataset
  reservations: ReservationItem[]
  addReservation: (draft: ReservationDraft) => ReservationActionResult
  updateReservation: (id: string, draft: ReservationDraft) => ReservationActionResult
  cancelReservation: (id: string) => void
}

export const ParkingContext = createContext<ParkingContextValue | null>(null)

export function useParkingState(): ParkingContextValue {
  const ctx = useContext(ParkingContext)
  if (!ctx) {
    throw new Error('useParkingState must be used within a ParkingStateProvider')
  }
  return ctx
}
