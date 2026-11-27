import { afterEach, describe, expect, it, vi } from 'vitest'
import { FACILITY_ID } from '../config/facility'
import { ApiError, apiRequest } from './client'
import {
  cancelReservation,
  commitChange,
  createReservation,
  loadFacility,
  recordEntry,
  recordExit,
  saveSettings,
  updateReservation,
} from './parkifyApi'

const dashboard = {
  facility_name: 'Skyline Autonomous Hub',
  snapshot_time: '2026-11-25T14:24:00',
  counts: {
    total: 1,
    available: 0,
    occupied: 1,
    reserved: 0,
    unavailable: 0,
    occupancy_percentage: '100.0',
  },
  rate_trend: '1/1 occupied',
  active_sessions: 1,
  overstay_sessions: 1,
  high_occupancy_alert_armed: true,
  above_high_occupancy_threshold: true,
  reservation_overstay_alert_armed: true,
  space_fault_alert_armed: false,
}

function occupancy(plate: string | null) {
  return {
    counts: dashboard.counts,
    zones: [
      {
        zone_id: 'zone-p2n',
        code: 'P2-N',
        name: 'Deck P2 North',
        category: 'Priority',
        occupied: 1,
        reserved: 0,
        unavailable: 0,
        available: 0,
        capacity: 1,
      },
    ],
    spots: [
      {
        spot_id: 'bay-p204',
        code: 'P-204',
        floor_code: 'P2',
        zone_id: 'zone-p2n',
        zone_code: 'P2-N',
        zone_name: 'Deck P2 North',
        bay_class: 'VIP Priority',
        status: 'occupied',
        hourly_rate: '6.00',
        maintenance_reason: null,
        plate_number: plate,
        session_id: 'ses-1',
        reservation_id: null,
        reserved_until: null,
      },
    ],
  }
}

const session = {
  id: 'ses-1',
  spot_code: 'P-204',
  plate_number: 'VEL-204X',
  status: 'Active',
  started_at: '2026-11-25T08:00:00',
  paid_until: '2026-11-25T14:08:00',
  has_alert: false,
  alert_title: null,
}

let reservations: { id: string; spot_code: string; plate_number: string; driver_name: null; status: string; effective_status: string; starts_at: string; ends_at: string }[] = []
let sessions = [session]
const storedSettings = {
  facility_name: 'Skyline Autonomous Hub',
  facility_address: '13 Skyline',
  operating_hours: '24/7',
  hourly_rate: '4.20',
  daily_max_rate: '28.00',
  grace_period_minutes: 15,
  ev_surcharge: '0.60',
  high_occupancy_alert: true,
  reservation_overstay_alert: true,
  space_fault_alert: true,
}

function installFetch() {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/dashboard')) return json(dashboard)
      if (url.endsWith('/occupancy')) return json(occupancy('VEL-204X'))
      if (url.endsWith('/reservations') && (!init?.method || init.method === 'GET')) {
        return json({ items: reservations })
      }
      if (url.endsWith('/cancellation') && init?.method === 'POST') {
        const id = url.split('/').at(-2)
        reservations = reservations.map((item) =>
          item.id === id ? { ...item, status: 'Cancelled', effective_status: 'Cancelled' } : item,
        )
        return json({ ok: true })
      }
      if (url.includes('/reservations/') && init?.method === 'PATCH') {
        const id = url.split('/').at(-1)
        const body = JSON.parse(String(init.body))
        reservations = reservations.map((item) =>
          item.id === id
            ? {
                ...item,
                spot_code: body.spot_code,
                plate_number: body.plate_number,
                starts_at: body.starts_at,
                ends_at: body.ends_at,
              }
            : item,
        )
        return json({ ok: true })
      }
      if (url.endsWith('/entries') && init?.method === 'POST') {
        const body = JSON.parse(String(init.body))
        sessions = [
          ...sessions,
          {
            ...session,
            id: 'ses-new',
            spot_code: body.spot_code,
            plate_number: body.plate_number,
          },
        ]
        return json({ ok: true }, 201)
      }
      if (url.endsWith('/exits') && init?.method === 'POST') {
        const body = JSON.parse(String(init.body))
        sessions = sessions.filter((item) => item.plate_number !== body.plate_number)
        return json({ ok: true })
      }
      if (url.endsWith('/reservations') && init?.method === 'POST') {
        const body = JSON.parse(String(init.body))
        if (body.plate_number === 'BAD') {
          return json({ error: { code: 'reservation_overlap', message: 'Overlap detected.' } }, 409)
        }
        reservations = [
          ...reservations,
          {
            id: 'res-new',
            spot_code: body.spot_code,
            plate_number: body.plate_number,
            driver_name: null,
            status: 'Scheduled',
            effective_status: 'Scheduled',
            starts_at: body.starts_at,
            ends_at: body.ends_at,
          },
        ]
        return json(reservations[0], 201)
      }
      if (url.endsWith('/settings') && init?.method === 'PATCH') {
        Object.assign(storedSettings, JSON.parse(String(init.body)))
        return json(storedSettings)
      }
      if (url.endsWith('/settings') && (!init?.method || init.method === 'GET')) {
        return json(storedSettings)
      }
      if (url.endsWith('/sessions')) return json({ items: sessions })
      if (url.includes('/gate-activity')) return json({ items: [], total: 0, limit: 20, offset: 0 })
      if (url.includes('/analytics/occupancy')) {
        return json({
          has_history: true,
          points: [
            {
              label: '2026-11-25 14:00',
              occupied: 1,
              capacity: 1,
              occupancy_percentage: '100.0',
            },
          ],
        })
      }
      return json({ error: { code: 'not_found', message: 'Missing' } }, 404)
    }),
  )
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => {
  reservations = []
  sessions = [session]
  storedSettings.hourly_rate = '4.20'
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('api client', () => {
  it('returns the server message for a conflict', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => json({ error: { code: 'spot_occupied', message: 'Space P-210 is occupied.' } }, 409)),
    )
    await expect(apiRequest(`/api/facilities/${FACILITY_ID}/entries`, { method: 'POST', body: {} })).rejects.toMatchObject({
      status: 409,
      code: 'spot_occupied',
      message: 'Space P-210 is occupied.',
    })
  })

  it('reports a network failure without credentials', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('failed'))))
    await expect(apiRequest('/api/health')).rejects.toBeInstanceOf(ApiError)
    await expect(apiRequest('/api/health')).rejects.toMatchObject({ code: 'network_error' })
  })
})

describe('facility loading and mutations', () => {
  it('maps live occupancy, decimals, and historical points', async () => {
    installFetch()
    const snapshot = await loadFacility()
    expect(snapshot.dataset.occupiedSpots).toBe(1)
    expect(snapshot.dataset.occupancyRate).toBe(100)
    expect(snapshot.dataset.bays[0]?.code).toBe('P-204')
    expect(snapshot.dataset.bays[0]?.row).toBe('north')
    expect(snapshot.dataset.bays[0]?.vehicle?.plateNumber).toBe('VEL-204X')
    expect(snapshot.settings.hourlyRate).toBeCloseTo(4.2)
    expect(snapshot.dataset.todayOccupancySeries).toEqual([
      { label: '14h', occupancyPct: 100, vehicles: 1 },
    ])
    expect(snapshot.dataset.yearlyRentalSeries).toEqual([])
    expect(snapshot.dataset.gateLogs).toEqual([])
  })

  it('keeps the previous snapshot when a reservation is rejected', async () => {
    installFetch()
    const before = await loadFacility()
    const result = await commitChange(() =>
      Promise.reject(new ApiError(409, 'reservation_overlap', 'Overlap detected.')),
    )
    expect(result.ok).toBe(false)
    if (!result.ok) expect(result.error).toBe('Overlap detected.')
    expect(before.reservations).toEqual([])
  })

  it('shows a created reservation only after the reload confirms it', async () => {
    installFetch()
    const before = await loadFacility()
    const result = await commitChange(async () => {
      reservations = [
        {
          id: 'res-new',
          spot_code: 'P-210',
          plate_number: 'API-200',
          driver_name: null,
          status: 'Scheduled',
          effective_status: 'Scheduled',
          starts_at: '2026-11-26T09:00:00',
          ends_at: '2026-11-26T11:00:00',
        },
      ]
    })
    expect(before.reservations).toEqual([])
    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.snapshot.reservations.map((item) => item.plateNumber)).toEqual(['API-200'])
    }
    const refreshed = await loadFacility()
    expect(refreshed.reservations.map((item) => item.id)).toEqual(['res-new'])
  })

  it('rejects a second mutation while the first is still running', async () => {
    installFetch()
    let release: () => void = () => {}
    const gate = new Promise<void>((resolve) => {
      release = resolve
    })
    const first = commitChange(() => gate)
    const second = await commitChange(async () => {})
    expect(second).toEqual({
      ok: false,
      error: 'Please wait for the current request to finish.',
    })
    release()
    const finished = await first
    expect(finished.ok).toBe(true)
  })

  it('sends settings money as decimal strings', async () => {
    installFetch()
    await saveSettings({
      facilityName: 'Skyline Autonomous Hub',
      facilityAddress: '13 Skyline',
      operatingHours: '24/7',
      hourlyRate: 4.2,
      dailyMaxRate: 28,
      gracePeriodMinutes: 15,
      evSurcharge: 0.6,
      highOccupancyAlert: true,
      reservationOverstayAlert: true,
      spaceFaultAlert: true,
    })
    const fetchMock = vi.mocked(fetch)
    const call = fetchMock.mock.calls.find((item) => String(item[0]).endsWith('/settings') && item[1]?.method === 'PATCH')
    const body = JSON.parse(String(call?.[1]?.body))
    expect(body.hourly_rate).toBe('4.20')
    expect(body.daily_max_rate).toBe('28.00')
    expect(body.ev_surcharge).toBe('0.60')
    expect(body).not.toHaveProperty('DATABASE_URL')
  })

  it('creates, edits, and cancels a reservation, then records entry and exit', async () => {
    installFetch()
    const draft = {
      plateNumber: 'API-200',
      bayCode: 'P-210',
      date: '2026-11-26',
      startTime: '09:00',
      endTime: '11:00',
    }
    const created = await commitChange(() => createReservation(draft))
    expect(created.ok).toBe(true)
    if (!created.ok) return
    expect(created.snapshot.reservations[0]).toMatchObject({
      plateNumber: 'API-200',
      bayCode: 'P-210',
      status: 'Scheduled',
    })

    const edited = await commitChange(() =>
      updateReservation('res-new', { ...draft, plateNumber: 'API-201', endTime: '12:00' }),
    )
    expect(edited.ok).toBe(true)
    if (!edited.ok) return
    expect(edited.snapshot.reservations[0]).toMatchObject({
      plateNumber: 'API-201',
      endTime: '12:00',
    })

    const cancelled = await commitChange(() => cancelReservation('res-new'))
    expect(cancelled.ok).toBe(true)
    if (!cancelled.ok) return
    expect(cancelled.snapshot.reservations[0]?.status).toBe('Cancelled')

    const entered = await commitChange(() => recordEntry('API-300', 'P-101'))
    expect(entered.ok).toBe(true)
    if (!entered.ok) return
    expect(entered.snapshot.sessions.map((item) => item.plateNumber)).toContain('API-300')

    const exited = await commitChange(() => recordExit('API-300'))
    expect(exited.ok).toBe(true)
    if (!exited.ok) return
    expect(exited.snapshot.sessions.map((item) => item.plateNumber)).not.toContain('API-300')
    expect(exited.snapshot.dataset.bays[0]?.code).toBe('P-204')

    const saved = await commitChange(() =>
      saveSettings({ ...created.snapshot.settings, hourlyRate: 5 }),
    )
    expect(saved.ok).toBe(true)
    if (!saved.ok) return
    expect(saved.snapshot.settings.hourlyRate).toBe(5)
    const refreshed = await loadFacility()
    expect(refreshed.settings.hourlyRate).toBe(5)
    expect(refreshed.reservations[0]?.status).toBe('Cancelled')
    expect(refreshed.sessions.map((item) => item.plateNumber)).toEqual(['VEL-204X'])
  })
})
