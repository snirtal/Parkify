export type KpiTone = 'primary' | 'emerald' | 'amber' | 'slate'

export interface HourlyOccupancyPoint {
  hour: string
  occupied: number
  capacity: number
}

export type ZoneCategory = 'Standard' | 'Commuter' | 'EV Charging' | 'Priority'

export interface ZoneCapacity {
  id: string
  name: string
  code: string
  category: ZoneCategory
  occupied: number
  capacity: number
}

export type GateEventType = 'entry' | 'exit'
export type GateSessionStatus = 'Active' | 'Completed' | 'Reserved'

export interface GateActivityEvent {
  id: string
  timestamp: string
  plateNumber: string
  eventType: GateEventType
  gateName: string
  zoneCode: string
  bayNumber: string
  status: GateSessionStatus
  duration?: string
}

export interface DashboardSnapshot {
  isSimulated: boolean
  facilityName: string
  snapshotTime: string
  totalSpots: number
  occupiedSpots: number
  availableSpots: number
  occupancyRate: number
  rateDeltaLabel: string
  hourlyOccupancy: HourlyOccupancyPoint[]
  zones: ZoneCapacity[]
  recentGateActivity: GateActivityEvent[]
}
