import type { DashboardSnapshot, ZoneCapacity, ZoneCategory } from '../types/dashboard'
import { SMART_PARKING_DATA } from './mockParkingData'

const CATEGORY_MAP: Record<string, ZoneCategory> = {
  'P2-N': 'Priority',
  'P2-S': 'EV Charging',
  'P1-N': 'Commuter',
  'P1-S': 'Standard',
}

const DERIVED_ZONES: ZoneCapacity[] = SMART_PARKING_DATA.zones.map((z) => ({
  id: z.id,
  name: z.name,
  code: z.code,
  category: CATEGORY_MAP[z.code] ?? 'Standard',
  occupied: z.occupied,
  reserved: z.reserved,
  unavailable: z.unavailable,
  capacity: z.capacity,
}))

export const MOCK_DASHBOARD_DATA: DashboardSnapshot = {
  isSimulated: SMART_PARKING_DATA.isSimulated,
  facilityName: SMART_PARKING_DATA.facilityName,
  snapshotTime: SMART_PARKING_DATA.snapshotTimestamp,
  totalSpots: SMART_PARKING_DATA.totalSpots,
  occupiedSpots: SMART_PARKING_DATA.occupiedSpots,
  availableSpots: SMART_PARKING_DATA.availableSpots,
  occupancyRate: SMART_PARKING_DATA.occupancyRate,
  rateDeltaLabel: SMART_PARKING_DATA.rateTrend,
  hourlyOccupancy: [
    { hour: '06:00', occupied: 6, capacity: SMART_PARKING_DATA.totalSpots },
    { hour: '08:00', occupied: 10, capacity: SMART_PARKING_DATA.totalSpots },
    { hour: '10:00', occupied: 18, capacity: SMART_PARKING_DATA.totalSpots },
    { hour: '11:00', occupied: 20, capacity: SMART_PARKING_DATA.totalSpots },
    { hour: '12:00', occupied: 22, capacity: SMART_PARKING_DATA.totalSpots },
    { hour: '13:00', occupied: 19, capacity: SMART_PARKING_DATA.totalSpots },
    { hour: '14:00', occupied: 16, capacity: SMART_PARKING_DATA.totalSpots },
    {
      hour: '14:24',
      occupied: SMART_PARKING_DATA.occupiedSpots,
      capacity: SMART_PARKING_DATA.totalSpots,
    },
  ],
  zones: DERIVED_ZONES,
  recentGateActivity: SMART_PARKING_DATA.gateLogs.map((log) => ({
    id: log.id,
    timestamp: log.timestamp,
    plateNumber: log.plateNumber,
    eventType: log.direction,
    gateName: log.gateName,
    zoneCode: log.bayCode.startsWith('P-2') ? 'P2' : 'P1',
    bayNumber: log.bayCode,
    status: log.status,
    duration: log.duration,
  })),
}
