export interface ApiSpot {
  spot_id: string
  code: string
  floor_code: string
  zone_id: string
  zone_code: string
  zone_name: string
  bay_class: 'Standard' | 'EV Fast 150kW' | 'VIP Priority' | 'Accessible'
  status: 'available' | 'occupied' | 'reserved' | 'unavailable'
  hourly_rate: string
  maintenance_reason: string | null
  plate_number: string | null
  session_id: string | null
  reservation_id: string | null
  reserved_until: string | null
}

export interface ApiZone {
  zone_id: string
  code: string
  name: string
  category: string
  occupied: number
  reserved: number
  unavailable: number
  available: number
  capacity: number
}

export interface ApiOccupancy {
  counts: {
    total: number
    available: number
    occupied: number
    reserved: number
    unavailable: number
    occupancy_percentage: string
  }
  zones: ApiZone[]
  spots: ApiSpot[]
}

export interface ApiDashboard {
  facility_name: string
  snapshot_time: string
  counts: ApiOccupancy['counts']
  rate_trend: string
  active_sessions: number
  overstay_sessions: number
  high_occupancy_alert_armed: boolean
  above_high_occupancy_threshold: boolean
  reservation_overstay_alert_armed: boolean
  space_fault_alert_armed: boolean
}

export interface ApiReservation {
  id: string
  spot_code: string
  plate_number: string
  driver_name: string | null
  status: 'Active' | 'Scheduled' | 'Completed' | 'Cancelled'
  effective_status: 'Active' | 'Scheduled' | 'Completed' | 'Cancelled'
  starts_at: string
  ends_at: string
}

export interface ApiSettings {
  facility_name: string
  facility_address: string
  operating_hours: string
  hourly_rate: string
  daily_max_rate: string
  grace_period_minutes: number
  ev_surcharge: string
  high_occupancy_alert: boolean
  reservation_overstay_alert: boolean
  space_fault_alert: boolean
}

export interface ApiSession {
  id: string
  spot_code: string
  plate_number: string
  status: string
  started_at: string
  paid_until: string | null
  has_alert: boolean
  alert_title: string | null
}

export interface ApiGateEvent {
  id: string
  occurred_at: string
  plate_number: string
  direction: 'entry' | 'exit'
  gate_name: string
  spot_code: string
  zone_code: string
  status: 'Active' | 'Completed' | 'Reserved'
  duration_label: string | null
  reservation_id: string | null
}

export interface ApiGatePage {
  items: ApiGateEvent[]
  total: number
  limit: number
  offset: number
}

export interface ApiOccupancyPoint {
  label: string
  occupied: number
  capacity: number
  occupancy_percentage: string
}

export interface ApiOccupancySeries {
  has_history: boolean
  points: ApiOccupancyPoint[]
}
