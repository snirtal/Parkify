import { lazy, Suspense, useState } from 'react'
import {
  BottomDeckCards,
  OccupancyHudBar,
  SpotInspectorPanel,
} from '../components/dashboard'
import { SMART_PARKING_DATA } from '../data/mockParkingData'
import './DashboardPage.css'

const IsometricGarage3D = lazy(() =>
  import('../components/garage3d/IsometricGarage3D').then((m) => ({
    default: m.IsometricGarage3D,
  })),
)

export function DashboardPage() {
  const [selectedBayId, setSelectedBayId] = useState<string>('bay-p204')

  const selectedBay =
    SMART_PARKING_DATA.bays.find((bay) => bay.id === selectedBayId) ??
    SMART_PARKING_DATA.bays[0]

  const handleSelectByCode = (bayCode: string) => {
    const target = SMART_PARKING_DATA.bays.find((b) => b.code === bayCode)
    if (target) {
      setSelectedBayId(target.id)
    }
  }

  return (
    <div className="cyber-dashboard">
      <div className="cyber-dashboard__stage-col">
        <OccupancyHudBar
          totalSpots={SMART_PARKING_DATA.totalSpots}
          availableSpots={SMART_PARKING_DATA.availableSpots}
          occupiedSpots={SMART_PARKING_DATA.occupiedSpots}
          reservedSpots={SMART_PARKING_DATA.reservedSpots}
          unavailableSpots={SMART_PARKING_DATA.unavailableSpots}
          occupancyRate={SMART_PARKING_DATA.occupancyRate}
          rateTrend={SMART_PARKING_DATA.rateTrend}
        />

        <Suspense
          fallback={
            <div className="cyber-dashboard__stage-skeleton" aria-busy="true">
              Initializing 3D Digital Twin…
            </div>
          }
        >
          <IsometricGarage3D
            bays={SMART_PARKING_DATA.bays}
            selectedBayId={selectedBay.id}
            snapshotTimestamp={SMART_PARKING_DATA.snapshotTimestamp}
            onSelectBay={setSelectedBayId}
          />
        </Suspense>

        <BottomDeckCards selectedBay={selectedBay} />
      </div>

      <div className="cyber-dashboard__inspector-col">
        <SpotInspectorPanel
          bay={selectedBay}
          zones={SMART_PARKING_DATA.zones}
          gateLogs={SMART_PARKING_DATA.gateLogs}
          yearlySeries={SMART_PARKING_DATA.yearlyRentalSeries}
          todaySeries={SMART_PARKING_DATA.todayOccupancySeries}
          onSelectBayByCode={handleSelectByCode}
        />
      </div>
    </div>
  )
}
