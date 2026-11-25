import { useEffect, useState, type ReactNode } from 'react'
import { isAbortError } from '../api/client'
import {
  cancelReservation as cancelReservationRequest,
  commitChange,
  createReservation,
  loadFacility,
  recordEntry as recordEntryRequest,
  recordExit as recordExitRequest,
  saveSettings,
  updateReservation as updateReservationRequest,
} from '../api/parkifyApi'
import type { FacilitySnapshot } from '../api/mapFacility'
import type { FacilitySettings, ReservationDraft, SmartParkingDataset } from '../types/parking'
import {
  ParkingContext,
  type ActionResult,
  type LoadStatus,
  type ParkingContextValue,
} from './useParkingState'

const EMPTY_SETTINGS: FacilitySettings = {
  facilityName: '',
  facilityAddress: '',
  operatingHours: '',
  hourlyRate: 0,
  dailyMaxRate: 0,
  gracePeriodMinutes: 0,
  evSurcharge: 0,
  highOccupancyAlert: false,
  reservationOverstayAlert: false,
  spaceFaultAlert: false,
}

const EMPTY_DATASET: SmartParkingDataset = {
  isSimulated: false,
  facilityAddress: '',
  facilityName: '',
  snapshotTimestamp: '',
  simulatedDate: '',
  simulatedTime: '',
  totalSpots: 0,
  availableSpots: 0,
  occupiedSpots: 0,
  reservedSpots: 0,
  unavailableSpots: 0,
  occupancyRate: 0,
  rateTrend: '',
  bays: [],
  todayOccupancySeries: [],
  yearlyRentalSeries: [],
  overstaySessions: 0,
  aboveHighOccupancy: false,
  zones: [],
  gateLogs: [],
  reservations: [],
}

export function ParkingStateProvider({ children }: { children: ReactNode }) {
  const [snapshot, setSnapshot] = useState<FacilitySnapshot | null>(null)
  const [status, setStatus] = useState<LoadStatus>('loading')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    loadFacility(controller.signal)
      .then((next) => {
        setSnapshot(next)
        setStatus('ready')
        setError(null)
      })
      .catch((loadError: unknown) => {
        if (isAbortError(loadError)) return
        setStatus('error')
        setError(loadError instanceof Error ? loadError.message : 'The facility could not be loaded.')
      })
    return () => controller.abort()
  }, [reloadKey])

  const apply = async (work: () => Promise<unknown>): Promise<ActionResult> => {
    setSubmitting(true)
    const result = await commitChange(work)
    setSubmitting(false)
    if (!result.ok) return result
    setSnapshot(result.snapshot)
    setStatus('ready')
    setError(null)
    return { ok: true }
  }

  const dataset = snapshot?.dataset ?? EMPTY_DATASET
  const settings = snapshot?.settings ?? EMPTY_SETTINGS

  const value: ParkingContextValue = {
    status,
    error,
    submitting,
    dataset,
    reservations: snapshot?.reservations ?? [],
    settings,
    sessions: snapshot?.sessions ?? [],
    reload: () => {
      setStatus('loading')
      setError(null)
      setReloadKey((key) => key + 1)
    },
    addReservation: (draft: ReservationDraft) => apply(() => createReservation(draft)),
    updateReservation: (id, draft) => apply(() => updateReservationRequest(id, draft)),
    cancelReservation: (id) => apply(() => cancelReservationRequest(id)),
    updateSettings: (next) => apply(() => saveSettings(next)),
    resetSettings: () => settings,
    recordEntry: (plateNumber, spotCode) => apply(() => recordEntryRequest(plateNumber, spotCode)),
    recordExit: (plateNumber) => apply(() => recordExitRequest(plateNumber)),
  }

  return <ParkingContext.Provider value={value}>{children}</ParkingContext.Provider>
}
