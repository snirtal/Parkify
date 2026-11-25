import { useMemo } from 'react'
import {
  DailyOccupancyChart,
  OccupancyHudBar,
  ZoneCapacityCard,
} from '../components/dashboard'
import { useParkingState } from '../context/useParkingState'
import { MOCK_DASHBOARD_DATA } from '../data/mockDashboardData'
import { deriveZoneCapacities } from '../utils/reservationUtils'
import './AnalyticsPage.css'

export function AnalyticsPage() {
  const { dataset } = useParkingState()
  const zones = useMemo(() => deriveZoneCapacities(dataset.zones), [dataset.zones])

  const hourlyData = useMemo(
    () =>
      MOCK_DASHBOARD_DATA.hourlyOccupancy.map((pt, idx, arr) =>
        idx === arr.length - 1
          ? { ...pt, occupied: dataset.occupiedSpots, capacity: dataset.totalSpots }
          : { ...pt, capacity: dataset.totalSpots },
      ),
    [dataset.occupiedSpots, dataset.totalSpots],
  )

  return (
    <div className="analytics-page">
      <OccupancyHudBar
        totalSpots={dataset.totalSpots}
        availableSpots={dataset.availableSpots}
        occupiedSpots={dataset.occupiedSpots}
        reservedSpots={dataset.reservedSpots}
        unavailableSpots={dataset.unavailableSpots}
        occupancyRate={dataset.occupancyRate}
        rateTrend={dataset.rateTrend}
      />

      <div className="analytics-grid">
        <DailyOccupancyChart
          data={hourlyData}
          totalCapacity={dataset.totalSpots}
          reservedSpots={dataset.reservedSpots}
          unavailableSpots={dataset.unavailableSpots}
        />
        <ZoneCapacityCard zones={zones} />
      </div>
    </div>
  )
}
