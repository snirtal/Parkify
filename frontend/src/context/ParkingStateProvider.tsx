import { useMemo, useState, type ReactNode } from 'react'
import { SMART_PARKING_DATA } from '../data/mockParkingData'
import type { ReservationDraft, ReservationItem } from '../types/parking'
import {
  computeReservationStatus,
  deriveParkingDataset,
  validateReservationDraft,
} from '../utils/reservationUtils'
import {
  ParkingContext,
  type ParkingContextValue,
  type ReservationActionResult,
} from './useParkingState'

export interface ParkingStateProviderProps {
  children: ReactNode
}

export function ParkingStateProvider({ children }: ParkingStateProviderProps) {
  const [reservations, setReservations] = useState<ReservationItem[]>(
    SMART_PARKING_DATA.reservations,
  )

  const addReservation = (draft: ReservationDraft): ReservationActionResult => {
    const cleanDraft: ReservationDraft = {
      ...draft,
      plateNumber: draft.plateNumber.trim().toUpperCase(),
    }

    const validationError = validateReservationDraft(
      cleanDraft,
      reservations,
      SMART_PARKING_DATA.bays,
      SMART_PARKING_DATA.simulatedDate,
    )
    if (validationError) {
      return { ok: false, error: validationError }
    }

    const nextItem: ReservationItem = {
      id: `res-${Date.now()}`,
      plateNumber: cleanDraft.plateNumber,
      bayCode: cleanDraft.bayCode,
      date: cleanDraft.date,
      startTime: cleanDraft.startTime,
      endTime: cleanDraft.endTime,
      status: computeReservationStatus(
        cleanDraft,
        SMART_PARKING_DATA.simulatedDate,
        SMART_PARKING_DATA.simulatedTime,
      ),
    }

    setReservations((prev) => [nextItem, ...prev])
    return { ok: true }
  }

  const updateReservation = (
    id: string,
    draft: ReservationDraft,
  ): ReservationActionResult => {
    const cleanDraft: ReservationDraft = {
      ...draft,
      plateNumber: draft.plateNumber.trim().toUpperCase(),
    }

    const validationError = validateReservationDraft(
      cleanDraft,
      reservations,
      SMART_PARKING_DATA.bays,
      SMART_PARKING_DATA.simulatedDate,
      id,
    )
    if (validationError) {
      return { ok: false, error: validationError }
    }

    setReservations((prev) =>
      prev.map((item) => {
        if (item.id !== id) return item
        return {
          ...item,
          plateNumber: cleanDraft.plateNumber,
          bayCode: cleanDraft.bayCode,
          date: cleanDraft.date,
          startTime: cleanDraft.startTime,
          endTime: cleanDraft.endTime,
          status: computeReservationStatus(
            cleanDraft,
            SMART_PARKING_DATA.simulatedDate,
            SMART_PARKING_DATA.simulatedTime,
          ),
        }
      }),
    )

    return { ok: true }
  }

  const cancelReservation = (id: string) => {
    setReservations((prev) =>
      prev.map((item) => (item.id === id ? { ...item, status: 'Cancelled' } : item)),
    )
  }

  const dataset = useMemo(
    () => deriveParkingDataset(SMART_PARKING_DATA, reservations),
    [reservations],
  )

  const value: ParkingContextValue = {
    dataset,
    reservations,
    addReservation,
    updateReservation,
    cancelReservation,
  }

  return <ParkingContext.Provider value={value}>{children}</ParkingContext.Provider>
}
