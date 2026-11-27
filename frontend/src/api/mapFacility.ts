import { placementForCode } from '../data/bayLayout'
import type { ChartSlotPoint, FacilitySettings, GateLogItem, ParkingBay, ReservationItem, ReservationRequestItem, SmartParkingDataset, ZoneBreakdownItem } from '../types/parking'
import type { ActiveSessionRow } from '../types/sessions'
import type {
  ApiDashboard,
  ApiGateEvent,
  ApiOccupancy,
  ApiOccupancySeries,
  ApiReservation,
  ApiSession,
  ApiSettings,
  ApiSpot,
  ApiZone,
} from './types'

const ZONE_ACCENT: Record<string, ZoneBreakdownItem['accent']> = {
  'P2-N': 'purple',
  'P2-S': 'cyan',
  'P1-N': 'blue',
  'P1-S': 'crimson',
}

export interface FacilitySnapshot {
  dataset: SmartParkingDataset
  reservations: ReservationItem[]
  reservationRequests: ReservationRequestItem[]
  settings: FacilitySettings
  sessions: ActiveSessionRow[]
}

export function mapFacility(
  occupancy: ApiOccupancy,
  dashboard: ApiDashboard,
  reservations: ApiReservation[],
  settings: ApiSettings,
  sessions: ApiSession[],
  gateEvents: ApiGateEvent[],
  series: ApiOccupancySeries,
): FacilitySnapshot {
  const mappedReservations = reservations.map(mapReservation)
  const mappedSessions = sessions.map(mapSession)
  const sessionBySpot = new Map(mappedSessions.map((session) => [session.bayCode, session]))
  const reservationById = new Map(mappedReservations.map((item) => [item.id, item]))
  const clock = splitTimestamp(dashboard.snapshot_time)

  const bays = occupancy.spots.flatMap((spot) => {
    const bay = mapSpot(spot, sessionBySpot.get(spot.code), reservationById)
    return bay ? [bay] : []
  })

  return {
    reservations: mappedReservations,
    reservationRequests: [],
    settings: mapSettings(settings),
    sessions: mappedSessions,
    dataset: {
      isSimulated: false,
      facilityName: settings.facility_name,
      facilityAddress: settings.facility_address,
      snapshotTimestamp: formatClock(dashboard.snapshot_time),
      simulatedDate: clock.date,
      simulatedTime: clock.time,
      totalSpots: occupancy.counts.total,
      availableSpots: occupancy.counts.available,
      occupiedSpots: occupancy.counts.occupied,
      reservedSpots: occupancy.counts.reserved,
      unavailableSpots: occupancy.counts.unavailable,
      occupancyRate: Number(occupancy.counts.occupancy_percentage),
      rateTrend: dashboard.rate_trend,
      bays,
      zones: occupancy.zones.map(mapZone),
      gateLogs: gateEvents.map(mapGate),
      reservations: mappedReservations,
      todayOccupancySeries: series.has_history ? series.points.map(mapPoint) : [],
      yearlyRentalSeries: [],
      overstaySessions: dashboard.overstay_sessions,
      aboveHighOccupancy: dashboard.above_high_occupancy_threshold,
    },
  }
}

function mapSpot(
  spot: ApiSpot,
  session: ActiveSessionRow | undefined,
  reservations: Map<string, ReservationItem>,
): ParkingBay | null {
  const placement = placementForCode(spot.code)
  if (placement === null) return null
  const reservation = spot.reservation_id ? reservations.get(spot.reservation_id) : undefined
  const bay: ParkingBay = {
    id: spot.spot_id,
    code: spot.code,
    deck: placement.deck,
    row: placement.row,
    slotIndex: placement.slotIndex,
    status: spot.status,
    bayClass: spot.bay_class,
    ratePerHour: spot.hourly_rate ? `$${spot.hourly_rate}/h` : '',
    sensorNote: sensorNote(spot),
  }
  if (spot.maintenance_reason) bay.maintenanceReason = spot.maintenance_reason
  if (spot.status === 'reserved' && spot.plate_number) {
    bay.reservedPlate = spot.plate_number
    bay.reservedBy = reservation?.driverName || 'Reserved'
    bay.reservedUntil = spot.reserved_until ? dottedClock(spot.reserved_until) : undefined
  }
  if (spot.status === 'occupied' && spot.plate_number) {
    bay.vehicle = {
      model: 'Parked vehicle',
      plateNumber: spot.plate_number,
      bodyType: 'Sedan',
      colorHex: '#94a3b8',
      accentHex: '#cbd5e1',
      driverName: '',
      driverInitials: spot.plate_number.slice(0, 2),
      monitoringLabel: session?.alertTitle || 'Active session',
      untilTime: session?.paidUntil ? dottedClock(session.paidUntil) : '--.--',
      untilCaption: 'Paid parking time',
      hasAlert: session?.hasAlert,
      alertTitle: session?.alertTitle ?? undefined,
    }
  }
  return bay
}

function sensorNote(spot: ApiSpot): string {
  if (spot.maintenance_reason) return spot.maintenance_reason
  if (spot.status === 'occupied' && spot.plate_number) return `Occupied by ${spot.plate_number}.`
  if (spot.status === 'reserved' && spot.plate_number) return `Reserved for ${spot.plate_number}.`
  return 'Available.'
}

function mapZone(zone: ApiZone): ZoneBreakdownItem {
  return {
    id: zone.zone_id,
    code: zone.code,
    name: zone.name,
    category: zone.category,
    occupied: zone.occupied,
    reserved: zone.reserved,
    unavailable: zone.unavailable,
    capacity: zone.capacity,
    accent: ZONE_ACCENT[zone.code] ?? 'blue',
  }
}

function mapReservation(item: ApiReservation): ReservationItem {
  const start = splitTimestamp(item.starts_at)
  const end = splitTimestamp(item.ends_at)
  return {
    id: item.id,
    plateNumber: item.plate_number,
    bayCode: item.spot_code,
    date: start.date,
    startTime: start.time,
    endTime: end.time,
    status: item.effective_status,
    driverName: item.driver_name ?? undefined,
  }
}

function mapSession(item: ApiSession): ActiveSessionRow {
  return {
    id: item.id,
    plateNumber: item.plate_number,
    bayCode: item.spot_code,
    startedAt: formatClock(item.started_at),
    paidUntil: item.paid_until,
    hasAlert: item.has_alert,
    alertTitle: item.alert_title,
    status: item.status,
  }
}

function mapGate(item: ApiGateEvent): GateLogItem {
  return {
    id: item.id,
    timestamp: formatClock(item.occurred_at),
    plateNumber: item.plate_number,
    direction: item.direction,
    gateName: item.gate_name,
    bayCode: item.spot_code,
    zoneCode: item.zone_code,
    status: item.status,
    duration: item.duration_label ?? undefined,
  }
}

function mapPoint(point: { label: string; occupied: number; occupancy_percentage: string }): ChartSlotPoint {
  const hour = point.label.slice(11, 13)
  return {
    label: `${hour}h`,
    occupancyPct: Number(point.occupancy_percentage),
    vehicles: point.occupied,
  }
}

function mapSettings(settings: ApiSettings): FacilitySettings {
  return {
    facilityName: settings.facility_name,
    facilityAddress: settings.facility_address,
    operatingHours: settings.operating_hours,
    hourlyRate: Number(settings.hourly_rate),
    dailyMaxRate: Number(settings.daily_max_rate),
    gracePeriodMinutes: settings.grace_period_minutes,
    evSurcharge: Number(settings.ev_surcharge),
    highOccupancyAlert: settings.high_occupancy_alert,
    reservationOverstayAlert: settings.reservation_overstay_alert,
    spaceFaultAlert: settings.space_fault_alert,
  }
}

export function moneyString(value: number): string {
  return value.toFixed(2)
}

export function reservationWindow(date: string, time: string): string {
  return `${date}T${time.length === 5 ? `${time}:00` : time}`
}

function splitTimestamp(value: string): { date: string; time: string } {
  const [date, clock = '00:00:00'] = value.split('T')
  return { date, time: clock.slice(0, 5) }
}

function formatClock(value: string): string {
  return value.replace('T', ' ').slice(0, 19)
}

function dottedClock(value: string): string {
  return value.slice(11, 16).replace(':', '.')
}
