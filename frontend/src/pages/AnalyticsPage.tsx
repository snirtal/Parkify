import { useMemo } from 'react'
import {
  DailyOccupancyChart,
  OccupancyHudBar,
  ZoneCapacityCard,
} from '../components/dashboard'
import { useParkingState } from '../context/useParkingState'
import { deriveZoneCapacities } from '../utils/reservationUtils'
import './AnalyticsPage.css'

export function AnalyticsPage() {
  const { dataset } = useParkingState()
  const zones = useMemo(() => deriveZoneCapacities(dataset.zones), [dataset.zones])

  const hourlyData = useMemo(
    () =>
      dataset.todayOccupancySeries.map((point) => ({
        hour: point.label,
        occupied: point.vehicles,
        capacity: dataset.totalSpots,
      })),
    [dataset.todayOccupancySeries, dataset.totalSpots],
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
        {hourlyData.length === 0 ? (
          <section className="dashboard-panel occupancy-chart">
            <p className="facility-status">No stored occupancy for this day.</p>
          </section>
        ) : (
          <DailyOccupancyChart
            data={hourlyData}
            totalCapacity={dataset.totalSpots}
          />
        )}
        <ZoneCapacityCard zones={zones} />
      </div>
    </div>
  )
}
