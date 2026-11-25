import { lazy, Suspense, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { SpotInspectorPanel } from '../components/dashboard'
import { ParkingSearchBar } from '../components/parking-map/ParkingSearchBar'
import { matchBayQuery } from '../components/parking-map/searchUtils'
import { useParkingState } from '../context/useParkingState'
import './DashboardPage.css'

const IsometricGarage3D = lazy(() =>
  import('../components/garage3d/IsometricGarage3D').then((m) => ({
    default: m.IsometricGarage3D,
  })),
)

const DEFAULT_BAY_ID = 'bay-p204'

export function ParkingMapPage() {
  const { dataset } = useParkingState()
  const [searchParams, setSearchParams] = useSearchParams()
  const [searchQuery, setSearchQuery] = useState<string>('')

  const bayParam = searchParams.get('bay')

  const selectedBay = useMemo(() => {
    if (bayParam) {
      const normalized = bayParam.trim().toLowerCase()
      const matched = dataset.bays.find(
        (bay) => bay.code.toLowerCase() === normalized || bay.id.toLowerCase() === normalized,
      )
      if (matched) return matched
    }
    return (
      dataset.bays.find((bay) => bay.id === DEFAULT_BAY_ID) ??
      dataset.bays[0]
    )
  }, [bayParam, dataset.bays])

  const matchedBayIds = useMemo(() => {
    if (!searchQuery.trim()) return null
    const matching = dataset.bays
      .filter((bay) => matchBayQuery(bay, searchQuery))
      .map((bay) => bay.id)
    return new Set(matching)
  }, [dataset.bays, searchQuery])

  const handleSelectBay = (bayId: string) => {
    const target = dataset.bays.find((b) => b.id === bayId)
    if (target) {
      setSearchParams({ bay: target.code }, { replace: true })
    }
  }

  const handleSelectByCode = (bayCode: string) => {
    const target = dataset.bays.find((b) => b.code === bayCode)
    if (target) {
      setSearchParams({ bay: target.code }, { replace: true })
    }
  }

  if (!selectedBay) {
    return <p className="facility-status">No parking spots were returned.</p>
  }

  return (
    <div className="cyber-dashboard">
      <div className="cyber-dashboard__stage-col">
        <ParkingSearchBar
          bays={dataset.bays}
          selectedBayId={selectedBay.id}
          query={searchQuery}
          onQueryChange={setSearchQuery}
          onSelectBay={handleSelectBay}
        />

        <Suspense
          fallback={
            <div
              className="cyber-dashboard__stage-skeleton cyber-dashboard__stage-skeleton--expanded"
              aria-busy="true"
            >
              Initializing 3D Digital Twin…
            </div>
          }
        >
          <IsometricGarage3D
            bays={dataset.bays}
            selectedBayId={selectedBay.id}
            snapshotTimestamp={dataset.snapshotTimestamp}
            onSelectBay={handleSelectBay}
            expanded
            matchedBayIds={matchedBayIds}
          />
        </Suspense>
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
