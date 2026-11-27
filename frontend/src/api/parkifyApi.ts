import type { FacilitySettings, ReservationDraft } from '../types/parking'
import { permissionsForRole, RESERVATIONS_READ, SESSIONS_READ, GATE_READ, SETTINGS_READ } from '../auth/permissions'
import { FACILITY_ID } from '../config/facility'
import { apiRequest } from './client'
import { mapFacility, moneyString, reservationWindow, type FacilitySnapshot } from './mapFacility'
import type {
  ApiDashboard,
  ApiGatePage,
  ApiOccupancy,
  ApiOccupancySeries,
  ApiReservation,
  ApiSession,
  ApiSettings,
} from './types'

const root = `/api/facilities/${FACILITY_ID}`

export async function loadFacility(
  signal?: AbortSignal,
  granted: ReadonlySet<string> = permissionsForRole('admin'),
): Promise<FacilitySnapshot> {
  const dashboard = await apiRequest<ApiDashboard>(`${root}/dashboard`, { signal })
  const date = dashboard.snapshot_time.slice(0, 10)
  const occupancy = await apiRequest<ApiOccupancy>(`${root}/occupancy`, { signal })
  const reservationPage = granted.has(RESERVATIONS_READ)
    ? await apiRequest<{ items: ApiReservation[] }>(`${root}/reservations`, { signal })
    : { items: [] }
  const settings = granted.has(SETTINGS_READ)
    ? await apiRequest<ApiSettings>(`${root}/settings`, { signal })
    : settingsFromDashboard(dashboard)
  const sessionPage = granted.has(SESSIONS_READ)
    ? await apiRequest<{ items: ApiSession[] }>(`${root}/sessions`, { signal })
    : { items: [] }
  const gatePage = granted.has(GATE_READ)
    ? await apiRequest<ApiGatePage>(`${root}/gate-activity?limit=20`, { signal })
    : { items: dashboard.recent_gate_activity ?? [] }
  const series = granted.has('occupancy.read')
    ? await apiRequest<ApiOccupancySeries>(
        `${root}/analytics/occupancy?start=${date}T00:00:00&end=${date}T23:59:00&bucket_minutes=60`,
        { signal },
      )
    : { has_history: false, points: [] }
  return mapFacility(
    occupancy,
    dashboard,
    reservationPage.items,
    settings,
    sessionPage.items,
    gatePage.items,
    series,
  )
}

function settingsFromDashboard(dashboard: ApiDashboard): ApiSettings {
  return {
    facility_name: dashboard.facility_name,
    facility_address: '',
    operating_hours: '',
    hourly_rate: '',
    daily_max_rate: '',
    grace_period_minutes: 0,
    ev_surcharge: '',
    high_occupancy_alert: dashboard.high_occupancy_alert_armed,
    reservation_overstay_alert: dashboard.reservation_overstay_alert_armed,
    space_fault_alert: dashboard.space_fault_alert_armed,
  }
}

let inFlight = false

export async function commitChange(
  work: () => Promise<unknown>,
): Promise<{ ok: true; snapshot: FacilitySnapshot } | { ok: false; error: string }> {
  if (inFlight) {
    return { ok: false, error: 'Please wait for the current request to finish.' }
  }
  inFlight = true
  try {
    await work()
    return { ok: true, snapshot: await loadFacility() }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'The request failed.'
    return { ok: false, error: message }
  } finally {
    inFlight = false
  }
}

export function createReservation(draft: ReservationDraft) {
  return apiRequest<ApiReservation>(`${root}/reservations`, {
    method: 'POST',
    body: {
      plate_number: draft.plateNumber.trim(),
      spot_code: draft.bayCode,
      starts_at: reservationWindow(draft.date, draft.startTime),
      ends_at: reservationWindow(draft.date, draft.endTime),
    },
  })
}

export function updateReservation(id: string, draft: ReservationDraft) {
  return apiRequest<ApiReservation>(`${root}/reservations/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: {
      plate_number: draft.plateNumber.trim(),
      spot_code: draft.bayCode,
      starts_at: reservationWindow(draft.date, draft.startTime),
      ends_at: reservationWindow(draft.date, draft.endTime),
    },
  })
}

export function cancelReservation(id: string) {
  return apiRequest<ApiReservation>(
    `${root}/reservations/${encodeURIComponent(id)}/cancellation`,
    { method: 'POST', body: {} },
  )
}

export function saveSettings(settings: FacilitySettings) {
  return apiRequest<ApiSettings>(`${root}/settings`, {
    method: 'PATCH',
    body: {
      facility_name: settings.facilityName.trim(),
      facility_address: settings.facilityAddress.trim(),
      operating_hours: settings.operatingHours.trim(),
      hourly_rate: moneyString(settings.hourlyRate),
      daily_max_rate: moneyString(settings.dailyMaxRate),
      grace_period_minutes: Math.round(settings.gracePeriodMinutes),
      ev_surcharge: moneyString(settings.evSurcharge),
      high_occupancy_alert: settings.highOccupancyAlert,
      reservation_overstay_alert: settings.reservationOverstayAlert,
      space_fault_alert: settings.spaceFaultAlert,
    },
  })
}

export function recordEntry(plateNumber: string, spotCode: string) {
  return apiRequest(`${root}/entries`, {
    method: 'POST',
    body: { plate_number: plateNumber.trim(), spot_code: spotCode },
  })
}

export function recordExit(plateNumber: string) {
  return apiRequest(`${root}/exits`, {
    method: 'POST',
    body: { plate_number: plateNumber.trim() },
  })
}
