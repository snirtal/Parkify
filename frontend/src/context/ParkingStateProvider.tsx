import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { isAbortError } from '../api/client'
import { permissionsForRole } from '../auth/permissions'
import { useAuth } from '../auth/useAuth'
import {
  cancelReservation as cancelReservationRequest,
  approveReservationRequest as approveReservationRequestCall,
  commitChange,
  createReservation,
  loadFacility,
  recordEntry as recordEntryRequest,
  recordExit as recordExitRequest,
  rejectReservationRequest as rejectReservationRequestCall,
  saveSettings,
  updateReservation as updateReservationRequest,
} from '../api/parkifyApi'
import type { FacilitySnapshot } from '../api/mapFacility'
import type { FacilitySettings, ReservationDraft, SmartParkingDataset } from '../types/parking'
import { FACILITY_REFRESH_MS } from './liveRefresh'
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
  const { user } = useAuth()
  const granted = useMemo(() => permissionsForRole(user?.role), [user?.role])
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    let loaded = false
    let inFlight = false
    let active: AbortController | null = null

    const pull = () => {
      if (inFlight) return
      inFlight = true
      const controller = new AbortController()
      active = controller
      loadFacility(controller.signal, granted)
        .then((next) => {
          if (cancelled) return
          loaded = true
          setSnapshot(next)
          setStatus('ready')
          setError(null)
        })
        .catch((loadError: unknown) => {
          if (cancelled || isAbortError(loadError) || loaded) return
          setStatus('error')
          setError(loadError instanceof Error ? loadError.message : 'The facility could not be loaded.')
        })
        .finally(() => {
          if (active === controller) active = null
          inFlight = false
        })
    }

    pull()
    const timer = window.setInterval(pull, FACILITY_REFRESH_MS)
    return () => {
      cancelled = true
      active?.abort()
      window.clearInterval(timer)
    }
  }, [reloadKey, granted])

  const apply = async (work: () => Promise<unknown>): Promise<ActionResult> => {
    setSubmitting(true)
  const result = await commitChange(work, granted)
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
    reservationRequests: snapshot?.reservationRequests ?? [],
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
    approveReservationRequest: (id) => apply(() => approveReservationRequestCall(id)),
    rejectReservationRequest: (id) => apply(() => rejectReservationRequestCall(id)),
    updateSettings: (next) => apply(() => saveSettings(next)),
    resetSettings: () => settings,
    recordEntry: (plateNumber, spotCode) => apply(() => recordEntryRequest(plateNumber, spotCode)),
    recordExit: (plateNumber) => apply(() => recordExitRequest(plateNumber)),
  }

  return <ParkingContext.Provider value={value}>{children}</ParkingContext.Provider>
}
