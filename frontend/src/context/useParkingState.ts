import { createContext, useContext } from 'react'
import type {
  FacilitySettings,
  ReservationDraft,
  ReservationItem,
  SmartParkingDataset,
} from '../types/parking'
import type { ActiveSessionRow } from '../types/sessions'

export type LoadStatus = 'loading' | 'ready' | 'error'
export type ActionResult = { ok: true } | { ok: false; error: string }
export type ReservationActionResult = ActionResult

export interface ParkingContextValue {
  status: LoadStatus
  error: string | null
  submitting: boolean
  dataset: SmartParkingDataset
  reservations: ReservationItem[]
  settings: FacilitySettings
  sessions: ActiveSessionRow[]
  reload: () => void
  addReservation: (draft: ReservationDraft) => Promise<ReservationActionResult>
  updateReservation: (id: string, draft: ReservationDraft) => Promise<ReservationActionResult>
  cancelReservation: (id: string) => Promise<ActionResult>
  updateSettings: (next: FacilitySettings) => Promise<ActionResult>
  resetSettings: () => FacilitySettings
  recordEntry: (plateNumber: string, spotCode: string) => Promise<ActionResult>
  recordExit: (plateNumber: string) => Promise<ActionResult>
}

export const ParkingContext = createContext<ParkingContextValue | null>(null)

export function useParkingState(): ParkingContextValue {
  const ctx = useContext(ParkingContext)
  if (!ctx) {
    throw new Error('useParkingState must be used within a ParkingStateProvider')
  }
  return ctx
}
