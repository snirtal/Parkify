import { lazy, Suspense, useState } from 'react'
import {
  BottomDeckCards,
  OccupancyHudBar,
  SpotInspectorPanel,
} from '../components/dashboard'
import { useParkingState } from '../context/useParkingState'
import './DashboardPage.css'

const IsometricGarage3D = lazy(() =>
  import('../components/garage3d/IsometricGarage3D').then((m) => ({
    default: m.IsometricGarage3D,
  })),
)

export function DashboardPage() {
  const { dataset } = useParkingState()
  const [selectedBayId, setSelectedBayId] = useState<string>('bay-p204')

  const selectedBay =
    dataset.bays.find((bay) => bay.id === selectedBayId) ?? dataset.bays[0]

  if (!selectedBay) {
    return <p className="facility-status">No parking spots were returned.</p>
  }

  const handleSelectByCode = (bayCode: string) => {
    const target = dataset.bays.find((b) => b.code === bayCode)
    if (target) {
      setSelectedBayId(target.id)
    }
  }

  return (
    <div className="cyber-dashboard">
      <div className="cyber-dashboard__stage-col">
        <OccupancyHudBar
          totalSpots={dataset.totalSpots}
          availableSpots={dataset.availableSpots}
          occupiedSpots={dataset.occupiedSpots}
          reservedSpots={dataset.reservedSpots}
          unavailableSpots={dataset.unavailableSpots}
          occupancyRate={dataset.occupancyRate}
          rateTrend={dataset.rateTrend}
        />

        <Suspense
          fallback={
            <div className="cyber-dashboard__stage-skeleton" aria-busy="true">
              Initializing 3D Digital Twin…
            </div>
          }
        >
          <IsometricGarage3D
            bays={dataset.bays}
            selectedBayId={selectedBay.id}
            snapshotTimestamp={dataset.snapshotTimestamp}
            onSelectBay={setSelectedBayId}
          />
        </Suspense>

        <BottomDeckCards selectedBay={selectedBay} />
      </div>

      <div className="cyber-dashboard__inspector-col">
        <SpotInspectorPanel
          bay={selectedBay}
          zones={dataset.zones}
          gateLogs={dataset.gateLogs}
          yearlySeries={dataset.yearlyRentalSeries}
          todaySeries={dataset.todayOccupancySeries}
          onSelectBayByCode={handleSelectByCode}
        />
      </div>
    </div>
  )
}
