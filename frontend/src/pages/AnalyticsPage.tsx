import { useMemo } from 'react'
import { DailyOccupancyChart, ZoneCapacityCard } from '../components/dashboard'
import { useParkingState } from '../context/useParkingState'
import { MOCK_DASHBOARD_DATA } from '../data/mockDashboardData'
import { deriveZoneCapacities } from '../utils/reservationUtils'
import './AnalyticsPage.css'

export function AnalyticsPage() {
  const { dataset } = useParkingState()
  const zones = useMemo(() => deriveZoneCapacities(dataset.zones), [dataset.zones])

  return (
    <div className="analytics-grid">
      <DailyOccupancyChart
        data={MOCK_DASHBOARD_DATA.hourlyOccupancy}
        totalCapacity={dataset.totalSpots}
      />
      <ZoneCapacityCard zones={zones} />
    </div>
  )
}
