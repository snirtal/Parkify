import { DailyOccupancyChart, ZoneCapacityCard } from '../components/dashboard'
import { MOCK_DASHBOARD_DATA } from '../data/mockDashboardData'
import './AnalyticsPage.css'

export function AnalyticsPage() {
  return (
    <div className="analytics-grid">
      <DailyOccupancyChart
        data={MOCK_DASHBOARD_DATA.hourlyOccupancy}
        totalCapacity={MOCK_DASHBOARD_DATA.totalSpots}
      />
      <ZoneCapacityCard zones={MOCK_DASHBOARD_DATA.zones} />
    </div>
  )
}
