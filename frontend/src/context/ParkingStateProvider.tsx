import { useMemo, useState, type ReactNode } from 'react'
import { SMART_PARKING_DATA } from '../data/mockParkingData'
import type {
  FacilitySettings,
  ReservationDraft,
  ReservationItem,
} from '../types/parking'
import {
  computeReservationStatus,
  deriveParkingDataset,
  validateReservationDraft,
} from '../utils/reservationUtils'
import {
  clearStoredSettings,
  DEFAULT_FACILITY_SETTINGS,
  loadStoredSettings,
  saveStoredSettings,
  validateFacilitySettings,
} from '../utils/settingsUtils'
import {
  ParkingContext,
  type ActionResult,
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
  const [settings, setSettings] = useState<FacilitySettings>(() => loadStoredSettings())

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

  const updateSettings = (next: FacilitySettings): ActionResult => {
    const normalized: FacilitySettings = {
      ...next,
      facilityName: next.facilityName.trim(),
      facilityAddress: next.facilityAddress.trim(),
      operatingHours: next.operatingHours.trim(),
      hourlyRate: Number(next.hourlyRate.toFixed(2)),
      dailyMaxRate: Number(next.dailyMaxRate.toFixed(2)),
      gracePeriodMinutes: Math.round(next.gracePeriodMinutes),
      evSurcharge: Number(next.evSurcharge.toFixed(2)),
    }

    const validationError = validateFacilitySettings(normalized)
    if (validationError) {
      return { ok: false, error: validationError }
    }

    setSettings(normalized)
    saveStoredSettings(normalized)
    return { ok: true }
  }

  const resetSettings = (): FacilitySettings => {
    clearStoredSettings()
    setSettings(DEFAULT_FACILITY_SETTINGS)
    return DEFAULT_FACILITY_SETTINGS
  }

  const dataset = useMemo(
    () => deriveParkingDataset(SMART_PARKING_DATA, reservations, settings),
    [reservations, settings],
  )

  const value: ParkingContextValue = {
    dataset,
    reservations,
    settings,
    addReservation,
    updateReservation,
    cancelReservation,
    updateSettings,
    resetSettings,
  }

  return <ParkingContext.Provider value={value}>{children}</ParkingContext.Provider>
}
