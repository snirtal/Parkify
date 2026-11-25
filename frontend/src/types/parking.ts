export type BayStatus = 'available' | 'occupied' | 'reserved' | 'unavailable'

export type VehicleBodyType = 'Sedan' | 'SUV' | 'Coupe' | 'Crossover'

export interface BayVehicleInfo {
  model: string
  plateNumber: string
  bodyType: VehicleBodyType
  colorHex: string
  accentHex: string
  driverName: string
  driverInitials: string
  monitoringLabel: string
  untilTime: string
  untilCaption: string
  hasAlert?: boolean
  alertTitle?: string
  alertNote?: string
}

export interface ParkingBay {
  id: string
  code: string
  deck: 'P2' | 'P1'
  row: 'north' | 'south'
  slotIndex: number
  status: BayStatus
  bayClass: 'Standard' | 'EV Fast 150kW' | 'VIP Priority' | 'Accessible'
  ratePerHour: string
  sensorNote: string
  reservedBy?: string
  reservedPlate?: string
  reservedUntil?: string
  maintenanceReason?: string
  vehicle?: BayVehicleInfo
}

export interface ChartSlotPoint {
  label: string
  occupancyPct: number
  vehicles: number
  isHatched?: boolean
}

export interface ZoneBreakdownItem {
  id: string
  code: string
  name: string
  category: string
  occupied: number
  reserved: number
  unavailable: number
  capacity: number
  accent: 'purple' | 'cyan' | 'blue' | 'crimson'
}

export interface GateLogItem {
  id: string
  timestamp: string
  plateNumber: string
  direction: 'entry' | 'exit'
  gateName: string
  bayCode: string
  zoneCode?: string
  status: 'Active' | 'Completed' | 'Reserved'
  duration?: string
}

export type ReservationStatus = 'Active' | 'Scheduled' | 'Completed' | 'Cancelled'

export interface ReservationItem {
  id: string
  plateNumber: string
  bayCode: string
  date: string
  startTime: string
  endTime: string
  status: ReservationStatus
  driverName?: string
  linkedGateLogId?: string
  isSeeded?: boolean
}

export interface ReservationDraft {
  plateNumber: string
  bayCode: string
  date: string
  startTime: string
  endTime: string
}

export interface FacilitySettings {
  facilityName: string
  facilityAddress: string
  operatingHours: string
  hourlyRate: number
  dailyMaxRate: number
  gracePeriodMinutes: number
  evSurcharge: number
  highOccupancyAlert: boolean
  reservationOverstayAlert: boolean
  spaceFaultAlert: boolean
}

export interface SmartParkingDataset {
  isSimulated: boolean
  facilityAddress: string
  facilityName: string
  snapshotTimestamp: string
  simulatedDate: string
  simulatedTime: string
  totalSpots: number
  availableSpots: number
  occupiedSpots: number
  reservedSpots: number
  unavailableSpots: number
  occupancyRate: number
  rateTrend: string
  bays: ParkingBay[]
  todayOccupancySeries: ChartSlotPoint[]
  yearlyRentalSeries: ChartSlotPoint[]
  overstaySessions: number
  aboveHighOccupancy: boolean
  zones: ZoneBreakdownItem[]
  gateLogs: GateLogItem[]
  reservations: ReservationItem[]
}
