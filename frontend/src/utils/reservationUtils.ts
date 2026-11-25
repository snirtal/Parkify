import { normalizeSearchToken } from '../components/parking-map/searchUtils'
import type { GateActivityEvent, ZoneCapacity, ZoneCategory } from '../types/dashboard'
import type {
  GateLogItem,
  ParkingBay,
  ReservationDraft,
  ReservationItem,
  ReservationStatus,
  SmartParkingDataset,
  ZoneBreakdownItem,
} from '../types/parking'

export function toMinutes(timeStr: string): number {
  const normalized = timeStr.trim().replace('.', ':')
  const parts = normalized.split(':')
  if (parts.length !== 2) return Number.NaN
  const hours = Number(parts[0])
  const minutes = Number(parts[1])
  if (
    !Number.isInteger(hours) ||
    !Number.isInteger(minutes) ||
    hours < 0 ||
    hours > 23 ||
    minutes < 0 ||
    minutes > 59
  ) {
    return Number.NaN
  }
  return hours * 60 + minutes
}

export function computeReservationStatus(
  draft: ReservationDraft,
  simulatedDate: string,
  simulatedTime: string,
): ReservationStatus {
  if (draft.date < simulatedDate) return 'Completed'
  if (draft.date > simulatedDate) return 'Scheduled'

  const simMin = toMinutes(simulatedTime)
  const startMin = toMinutes(draft.startTime)
  const endMin = toMinutes(draft.endTime)

  if (endMin <= simMin) return 'Completed'
  if (startMin <= simMin && endMin > simMin) return 'Active'
  return 'Scheduled'
}

export function validateReservationDraft(
  draft: ReservationDraft,
  existingReservations: ReservationItem[],
  baseBays: ParkingBay[],
  simulatedDate: string,
  excludeId?: string,
): string | null {
  const normPlate = normalizeSearchToken(draft.plateNumber)
  if (normPlate.length < 2) {
    return 'Please enter a valid vehicle license plate.'
  }

  const targetBay = baseBays.find((bay) => bay.code === draft.bayCode)
  if (!targetBay) {
    return 'Please select a valid parking spot.'
  }

  if (targetBay.status === 'unavailable') {
    return `Space ${targetBay.code} is offline for maintenance and cannot be reserved.`
  }

  if (!draft.date || !draft.startTime || !draft.endTime) {
    return 'Please select a valid date, start time, and end time.'
  }

  const startMin = toMinutes(draft.startTime)
  const endMin = toMinutes(draft.endTime)
  if (Number.isNaN(startMin) || Number.isNaN(endMin) || endMin <= startMin) {
    return 'End time must be later than start time.'
  }

  if (draft.date === simulatedDate && targetBay.status === 'occupied' && targetBay.vehicle) {
    const untilFormatted = targetBay.vehicle.untilTime.replace('.', ':')
    const untilMin = toMinutes(untilFormatted)
    if (!Number.isNaN(untilMin) && startMin < untilMin) {
      return `Overlap detected: Space ${targetBay.code} is currently occupied by ${targetBay.vehicle.plateNumber} until ${untilFormatted} today.`
    }
  }

  for (const res of existingReservations) {
    if (res.id === excludeId || res.status === 'Cancelled') continue
    if (res.date !== draft.date) continue

    const resStart = toMinutes(res.startTime)
    const resEnd = toMinutes(res.endTime)
    const overlaps = startMin < resEnd && endMin > resStart
    if (!overlaps) continue

    if (res.bayCode === draft.bayCode) {
      return `Overlap detected: Space ${res.bayCode} is already reserved on ${res.date} from ${res.startTime} to ${res.endTime} (${res.plateNumber}).`
    }

    if (normalizeSearchToken(res.plateNumber) === normPlate) {
      return `Overlap detected: License plate ${res.plateNumber} already has a reservation in ${res.bayCode} from ${res.startTime} to ${res.endTime} on ${res.date}.`
    }
  }

  return null
}

function buildDerivedZone(
  baseZone: ZoneBreakdownItem,
  bays: ParkingBay[],
): ZoneBreakdownItem {
  const deck = baseZone.code.startsWith('P2') ? 'P2' : 'P1'
  const row = baseZone.code.endsWith('-N') ? 'north' : 'south'
  const subset = bays.filter((b) => b.deck === deck && b.row === row)

  return {
    ...baseZone,
    occupied: subset.filter((b) => b.status === 'occupied').length,
    reserved: subset.filter((b) => b.status === 'reserved').length,
    unavailable: subset.filter((b) => b.status === 'unavailable').length,
    capacity: subset.length,
  }
}

export function deriveParkingDataset(
  base: SmartParkingDataset,
  reservations: ReservationItem[],
): SmartParkingDataset {
  const derivedBays: ParkingBay[] = base.bays.map((bay) => {
    if (bay.status === 'occupied' || bay.status === 'unavailable') {
      return bay
    }

    const activeHolds = reservations
      .filter(
        (res) =>
          res.bayCode === bay.code &&
          res.date === base.simulatedDate &&
          (res.status === 'Active' || res.status === 'Scheduled'),
      )
      .sort((a, b) => {
        if (a.status !== b.status) return a.status === 'Active' ? -1 : 1
        return toMinutes(a.startTime) - toMinutes(b.startTime)
      })

    const hold = activeHolds[0]
    if (hold) {
      return {
        ...bay,
        status: 'reserved',
        reservedPlate: hold.plateNumber,
        reservedBy: hold.driverName ?? 'Reserved Pass Holder',
        reservedUntil: hold.endTime.replace(':', '.'),
        sensorNote: `License plate recognition armed for ${hold.plateNumber} (${hold.startTime}–${hold.endTime}).`,
      }
    }

    return {
      ...bay,
      status: 'available',
      reservedPlate: undefined,
      reservedBy: undefined,
      reservedUntil: undefined,
      sensorNote:
        bay.status === 'reserved'
          ? 'Bay clear and calibrated. Open for immediate check-in or reservation.'
          : bay.sensorNote,
    }
  })

  const derivedZones = base.zones.map((zone) => buildDerivedZone(zone, derivedBays))

  const syncedBaseLogs: GateLogItem[] = base.gateLogs.flatMap((log) => {
    const linked = reservations.find((r) => r.linkedGateLogId === log.id)
    if (!linked) return [log]
    if (linked.status === 'Cancelled') return []
    return [
      {
        ...log,
        plateNumber: linked.plateNumber,
        bayCode: linked.bayCode,
        status: linked.status === 'Completed' ? 'Completed' : 'Reserved',
      },
    ]
  })

  const newReservationLogs: GateLogItem[] = reservations
    .filter(
      (r) =>
        !r.linkedGateLogId &&
        !r.isSeeded &&
        r.date === base.simulatedDate &&
        (r.status === 'Active' || r.status === 'Scheduled'),
    )
    .map((r) => ({
      id: `gl-${r.id}`,
      timestamp: `${r.startTime}:00`,
      plateNumber: r.plateNumber,
      direction: 'entry' as const,
      gateName: r.bayCode.startsWith('P-2') ? 'Skyline North A' : 'South Express A',
      bayCode: r.bayCode,
      status: 'Reserved' as const,
    }))

  const derivedGateLogs = [...newReservationLogs, ...syncedBaseLogs]

  const totalSpots = derivedBays.length
  const occupiedSpots = derivedBays.filter((b) => b.status === 'occupied').length
  const availableSpots = derivedBays.filter((b) => b.status === 'available').length
  const reservedSpots = derivedBays.filter((b) => b.status === 'reserved').length
  const unavailableSpots = derivedBays.filter((b) => b.status === 'unavailable').length
  const occupancyRate = Number(((occupiedSpots / totalSpots) * 100).toFixed(1))

  return {
    ...base,
    totalSpots,
    occupiedSpots,
    availableSpots,
    reservedSpots,
    unavailableSpots,
    occupancyRate,
    rateTrend: `${occupiedSpots}/${totalSpots} occupied`,
    bays: derivedBays,
    zones: derivedZones,
    gateLogs: derivedGateLogs,
    reservations,
  }
}

const ZONE_CATEGORY_MAP: Record<string, ZoneCategory> = {
  'P2-N': 'Priority',
  'P2-S': 'EV Charging',
  'P1-N': 'Commuter',
  'P1-S': 'Standard',
}

export function deriveZoneCapacities(zones: ZoneBreakdownItem[]): ZoneCapacity[] {
  return zones.map((z) => ({
    id: z.id,
    name: z.name,
    code: z.code,
    category: ZONE_CATEGORY_MAP[z.code] ?? 'Standard',
    occupied: z.occupied,
    capacity: z.capacity,
  }))
}

export function deriveGateActivityEvents(gateLogs: GateLogItem[]): GateActivityEvent[] {
  return gateLogs.map((log) => ({
    id: log.id,
    timestamp: log.timestamp,
    plateNumber: log.plateNumber,
    eventType: log.direction,
    gateName: log.gateName,
    zoneCode: log.bayCode.startsWith('P-2') ? 'P2' : 'P1',
    bayNumber: log.bayCode,
    status: log.status,
    duration: log.duration,
  }))
}
